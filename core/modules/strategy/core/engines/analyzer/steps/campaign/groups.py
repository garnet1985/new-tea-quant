"""归因组号：``results/attribution/{n}/``，env_fp 只写进 meta，不当目录名。"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Set

logger = logging.getLogger(__name__)

ROOT_META_FILE = "meta.json"
GROUP_META_FILE = "group_meta.json"


class AttributionGroupStore:
    """env_fp → 从 1 起的短编号。同一环境复用同一号。"""

    @classmethod
    def resolve(cls, attribution_root: Path, env_fp: str) -> str:
        root = Path(attribution_root)
        root.mkdir(parents=True, exist_ok=True)
        fp = str(env_fp or "").strip()
        if not fp:
            raise ValueError("env_fp 不能为空")

        existing = cls._find_id(root, fp)
        if existing:
            return existing

        group_id = cls._allocate(root, fp)
        hash_dir = root / fp
        dest = root / group_id
        if hash_dir.is_dir() and hash_dir.resolve() != dest.resolve():
            if dest.exists():
                logger.warning("attribution group %s 已存在，留下旧哈希目录", group_id)
            else:
                hash_dir.rename(dest)
                logger.info("attribution group renamed %s → %s", fp[:8], group_id)
        return group_id

    @classmethod
    def _find_id(cls, root: Path, env_fp: str) -> Optional[str]:
        meta = cls._read_meta(root)
        registry = meta.get("registry")
        if isinstance(registry, dict):
            for gid, entry in registry.items():
                if not isinstance(entry, dict):
                    continue
                if str(entry.get("env_fp") or "").strip() == env_fp:
                    return str(gid).strip() or None
        if not root.is_dir():
            return None
        for child in sorted(root.iterdir(), key=_dir_sort_key):
            if not child.is_dir() or not child.name.isdigit():
                continue
            payload = _read_json(child / GROUP_META_FILE)
            if str(payload.get("env_fp") or "").strip() == env_fp:
                cls._remember(root, child.name, env_fp)
                return child.name
        return None

    @classmethod
    def _allocate(cls, root: Path, env_fp: str) -> str:
        meta = cls._read_meta(root)
        try:
            next_id = max(int(meta.get("next_group_id") or 1), 1)
        except (TypeError, ValueError):
            next_id = 1
        used = _used_ids(root, meta)
        while str(next_id) in used:
            next_id += 1
        group_id = str(next_id)
        meta["next_group_id"] = next_id + 1
        registry = dict(meta.get("registry") or {})
        registry[group_id] = {
            "env_fp": env_fp,
            "created_at": datetime.now().isoformat(),
        }
        meta["registry"] = registry
        _write_json(root / ROOT_META_FILE, meta)
        return group_id

    @classmethod
    def _remember(cls, root: Path, group_id: str, env_fp: str) -> None:
        meta = cls._read_meta(root)
        registry = dict(meta.get("registry") or {})
        current = registry.get(group_id)
        if isinstance(current, dict) and str(current.get("env_fp") or "") == env_fp:
            return
        entry = dict(current) if isinstance(current, dict) else {}
        entry["env_fp"] = env_fp
        entry.setdefault("created_at", datetime.now().isoformat())
        registry[group_id] = entry
        meta["registry"] = registry
        if not meta.get("next_group_id"):
            try:
                meta["next_group_id"] = int(group_id) + 1
            except (TypeError, ValueError):
                meta["next_group_id"] = 2
        _write_json(root / ROOT_META_FILE, meta)

    @classmethod
    def _read_meta(cls, root: Path) -> Dict[str, Any]:
        return _read_json(root / ROOT_META_FILE)


def _used_ids(root: Path, meta: Mapping[str, Any]) -> Set[str]:
    used = _registry_ids(meta)
    if root.is_dir():
        used |= {
            child.name
            for child in root.iterdir()
            if child.is_dir() and child.name.isdigit()
        }
    return used


def _registry_ids(meta: Mapping[str, Any]) -> Set[str]:
    registry = meta.get("registry")
    if not isinstance(registry, dict):
        return set()
    return {str(key).strip() for key in registry if str(key).strip()}


def _dir_sort_key(path: Path):
    name = path.name
    try:
        return (0, int(name))
    except (TypeError, ValueError):
        return (1, name)


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
