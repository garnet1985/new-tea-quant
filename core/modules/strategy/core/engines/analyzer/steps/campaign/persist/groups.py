"""归因组号：``results/attribution/{n}/``，env_fp 只写进 meta，不当目录名。"""
from __future__ import annotations

import hashlib
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

logger = logging.getLogger(__name__)

ROOT_META_FILE = "meta.json"
GROUP_META_FILE = "group_meta.json"


class AttributionGroupStore:
    """env_fp → 从 1 起的短编号。带 parent_version_id 时按策略版本各用一组。"""

    @classmethod
    def find(cls, attribution_root: Path, env_fp: str) -> Optional[str]:
        """只查组号，不分配。同一环境有多组时返回先登记的那组。"""
        fp = str(env_fp or "").strip()
        if not fp:
            return None
        return cls._find_id(Path(attribution_root), fp)

    @classmethod
    def find_for_version(
        cls,
        attribution_root: Path,
        env_fp: str,
        parent_version_id: str,
    ) -> Optional[str]:
        """查找锚定在该策略版本上的归因组，不分配。"""
        fp = str(env_fp or "").strip()
        parent = str(parent_version_id or "").strip()
        if not fp or not parent:
            return None
        return cls._find_id_for_version(Path(attribution_root), fp, parent)

    @classmethod
    def resolve(
        cls,
        attribution_root: Path,
        env_fp: str,
        parent_version_id: str = "",
    ) -> str:
        root = Path(attribution_root)
        root.mkdir(parents=True, exist_ok=True)
        fp = str(env_fp or "").strip()
        if not fp:
            raise ValueError("env_fp 不能为空")
        parent = str(parent_version_id or "").strip()

        if parent:
            existing = cls.find_for_version(root, fp, parent)
            if existing:
                return existing
            claimed = cls._claim_unstamped(root, fp, parent)
            if claimed:
                return claimed
            group_id = cls._allocate(root, fp, parent)
        else:
            existing = cls.find(root, fp)
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
    def _find_id_for_version(cls, root: Path, env_fp: str, parent: str) -> Optional[str]:
        meta = cls._read_meta(root)
        registry = meta.get("registry")
        if isinstance(registry, dict):
            for gid, entry in registry.items():
                if not isinstance(entry, dict):
                    continue
                if str(entry.get("env_fp") or "").strip() != env_fp:
                    continue
                if str(entry.get("parent_version_id") or "").strip() == parent:
                    return str(gid).strip() or None
        if not root.is_dir():
            return None
        for child in sorted(root.iterdir(), key=_dir_sort_key):
            if not child.is_dir() or not child.name.isdigit():
                continue
            payload = _read_json(child / GROUP_META_FILE)
            if str(payload.get("env_fp") or "").strip() != env_fp:
                continue
            stored = str(payload.get("parent_version_id") or "").strip()
            if stored == parent:
                cls._remember(root, child.name, env_fp, parent)
                return child.name
            if stored:
                continue
            if parent in _report_baselines(child):
                cls._remember(root, child.name, env_fp, parent)
                return child.name
        return None

    @classmethod
    def _claim_unstamped(cls, root: Path, env_fp: str, parent: str) -> Optional[str]:
        """还没有版本锚点、报告也不属于别的版本的组，归到这次的策略版本。"""
        if not root.is_dir():
            return None
        for child in sorted(root.iterdir(), key=_dir_sort_key):
            if not child.is_dir() or not child.name.isdigit():
                continue
            payload = _read_json(child / GROUP_META_FILE)
            meta = cls._read_meta(root)
            registry = meta.get("registry") if isinstance(meta.get("registry"), dict) else {}
            entry = registry.get(child.name) if isinstance(registry, dict) else None
            env = str(
                (payload.get("env_fp") if payload else "")
                or (entry.get("env_fp") if isinstance(entry, dict) else "")
                or ""
            ).strip()
            if env != env_fp:
                continue
            stored = str(
                (payload.get("parent_version_id") if payload else "")
                or (entry.get("parent_version_id") if isinstance(entry, dict) else "")
                or ""
            ).strip()
            if stored:
                continue
            baselines = _report_baselines(child)
            if baselines and parent not in baselines:
                continue
            cls._remember(root, child.name, env_fp, parent)
            return child.name
        return None

    @classmethod
    def _allocate(cls, root: Path, env_fp: str, parent_version_id: str = "") -> str:
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
        entry: Dict[str, Any] = {
            "env_fp": env_fp,
            "created_at": datetime.now().isoformat(),
        }
        parent = str(parent_version_id or "").strip()
        if parent:
            entry["parent_version_id"] = parent
        registry[group_id] = entry
        meta["registry"] = registry
        _write_json(root / ROOT_META_FILE, meta)
        return group_id

    @classmethod
    def _remember(
        cls,
        root: Path,
        group_id: str,
        env_fp: str,
        parent_version_id: str = "",
    ) -> None:
        meta = cls._read_meta(root)
        registry = dict(meta.get("registry") or {})
        current = registry.get(group_id)
        parent = str(parent_version_id or "").strip()
        if (
            isinstance(current, dict)
            and str(current.get("env_fp") or "") == env_fp
            and str(current.get("parent_version_id") or "").strip() == parent
        ):
            return
        entry = dict(current) if isinstance(current, dict) else {}
        entry["env_fp"] = env_fp
        if parent:
            entry["parent_version_id"] = parent
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
    def record_version(
        cls,
        attribution_root: Path,
        env_fp: str,
        version_id: str,
        *,
        start_date: str = "",
        end_date: str = "",
        entity_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """平时 Run / 战役共用：把一个 version 记进组，并按样本窗索引。"""
        vid = str(version_id or "").strip().lstrip("vV")
        if not vid:
            return {}
        group_id = cls.resolve(attribution_root, env_fp)
        group_dir = Path(attribution_root) / group_id
        group_dir.mkdir(parents=True, exist_ok=True)
        path = group_dir / GROUP_META_FILE
        existing = _read_json(path)
        versions = _union_version_ids(existing.get("versions"), [vid])
        samples = _merge_sample(
            existing.get("samples"),
            vid,
            start_date=str(start_date or "").strip(),
            end_date=str(end_date or "").strip(),
            entity_ids=list(entity_ids or []),
        )
        payload = {
            "group_id": group_id,
            "env_fp": str(env_fp or "").strip(),
            "updated_at": datetime.now().isoformat(),
            "versions": versions,
            "samples": samples,
            "tasks": list(existing.get("tasks") or []),
        }
        _write_json(path, payload)
        return payload

    @classmethod
    def remove(cls, attribution_root: Path, env_fp: str) -> bool:
        """删除一个过时环境对应的归因组目录与 registry 条目。"""
        fp = str(env_fp or "").strip()
        if not fp:
            return False
        root = Path(attribution_root)
        group_id = cls._find_id(root, fp)
        if not group_id:
            return False
        group_dir = root / group_id
        if group_dir.is_dir():
            shutil.rmtree(group_dir)
        meta = cls._read_meta(root)
        registry = dict(meta.get("registry") or {})
        registry.pop(group_id, None)
        meta["registry"] = registry
        _write_json(root / ROOT_META_FILE, meta)
        logger.info("pruned attribution group=%s env=%s", group_id, fp[:8])
        return True

    @classmethod
    def _read_meta(cls, root: Path) -> Dict[str, Any]:
        return _read_json(root / ROOT_META_FILE)


def _union_version_ids(*groups: Any) -> List[str]:
    seen: List[str] = []
    for group in groups:
        if not isinstance(group, Sequence) or isinstance(group, (str, bytes)):
            continue
        for item in group:
            vid = str(item or "").strip().lstrip("vV")
            if vid and vid not in seen:
                seen.append(vid)
    return sorted(seen, key=_version_sort_key)


def _merge_sample(
    existing: Any,
    version_id: str,
    *,
    start_date: str,
    end_date: str,
    entity_ids: Sequence[str],
) -> List[Dict[str, Any]]:
    samples: List[Dict[str, Any]] = []
    if isinstance(existing, list):
        for item in existing:
            if isinstance(item, dict):
                samples.append(dict(item))
    if not start_date and not end_date and not entity_ids:
        return samples
    universe_fp = _universe_fp(entity_ids)
    match = None
    for item in samples:
        if str(item.get("start_date") or "") != start_date:
            continue
        if str(item.get("end_date") or "") != end_date:
            continue
        if str(item.get("universe_fp") or "") != universe_fp:
            continue
        match = item
        break
    if match is None:
        match = {
            "start_date": start_date,
            "end_date": end_date,
            "universe_fp": universe_fp,
            "n_entities": len([str(x).strip() for x in entity_ids if str(x).strip()]),
            "versions": [],
        }
        samples.append(match)
    match["versions"] = _union_version_ids(match.get("versions"), [version_id])
    return samples


def _universe_fp(entity_ids: Sequence[str]) -> str:
    ids = sorted({str(item).strip() for item in entity_ids if str(item).strip()})
    raw = json.dumps(ids, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _version_sort_key(vid: str) -> Any:
    try:
        return (0, int(vid))
    except (TypeError, ValueError):
        return (1, vid)


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


def _report_baselines(group_dir: Path) -> Set[str]:
    found: Set[str] = set()
    if not group_dir.is_dir():
        return found
    for child in group_dir.iterdir():
        if not child.is_dir():
            continue
        payload = _read_json(child / "report.json")
        baseline = str(payload.get("baseline_version_id") or "").strip()
        if baseline:
            found.add(baseline)
    return found


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
