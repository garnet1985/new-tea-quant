"""仿真 version 注册表：仅 ``simulations/meta.json``。

根 meta 职责（索引层）：
- ``next_version_id``
- ``registry``：``{ vid: { created_at, settings_fp, env_fp, ... } }``（key 即 version id）

条目可扩展（如 ``pinned``、``keep_forever`` 等），与指纹并列。

带 value 的 effective settings 快照落在 ``{vid}/effective_settings.json``（三步共享）。

查 version 两条路径等价（均扫 registry，version 数量可承受）：
- 双指纹 → ``find_version_by_fingerprints``
- vid → ``get_registry_entry`` / ``resolve_version``
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts.consts import (
    EFFECTIVE_SETTINGS_FILE,
    RUNTIME_ENV_FILE,
)

_ROOT_META = "meta.json"
_STEP_DIRS = {
    SimulateKind.ENUMERATE: "enum",
    SimulateKind.PRICE_FACTOR: "price",
    SimulateKind.PORTFOLIO: "portfolio",
}


def read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


class VersionMetaStore:
    """读写 ``simulations/meta.json`` registry 与 ``{vid}/effective_settings.json``。"""

    @staticmethod
    def root_meta_path(simulations_root: Path) -> Path:
        return Path(simulations_root) / _ROOT_META

    @staticmethod
    def effective_settings_path(simulations_root: Path, version_id: str) -> Path:
        return (
            Path(simulations_root) / str(version_id).strip() / EFFECTIVE_SETTINGS_FILE
        )

    @classmethod
    def read_root_meta(cls, simulations_root: Path) -> Dict[str, Any]:
        return read_json(cls.root_meta_path(simulations_root))

    @classmethod
    def write_root_meta(
        cls, simulations_root: Path, payload: Dict[str, Any]
    ) -> None:
        write_json(cls.root_meta_path(simulations_root), payload)

    @classmethod
    def read_effective_settings(
        cls,
        simulations_root: Path,
        version_id: str,
    ) -> Optional[Dict[str, Any]]:
        payload = read_json(
            cls.effective_settings_path(simulations_root, version_id)
        )
        return dict(payload) if payload else None

    @classmethod
    def write_effective_settings(
        cls,
        simulations_root: Path,
        version_id: str,
        *,
        settings: Dict[str, Any],
        entity_ids: Optional[List[str]] = None,
    ) -> Path:
        vid = str(version_id or "").strip()
        path = cls.effective_settings_path(simulations_root, vid)
        if path.is_file():
            return path
        body: Dict[str, Any] = dict(settings or {})
        if entity_ids is not None:
            body["entity_ids"] = [
                str(x).strip() for x in entity_ids if str(x).strip()
            ]
        write_json(path, body)
        return path

    @classmethod
    def _registry(cls, root_meta: Dict[str, Any]) -> Dict[str, Any]:
        reg = root_meta.get("registry")
        return dict(reg) if isinstance(reg, dict) else {}

    @staticmethod
    def _entry_settings_fp(entry: Dict[str, Any]) -> str:
        if str(entry.get("settings_fp") or "").strip():
            return str(entry.get("settings_fp") or "").strip()
        nested = entry.get("fingerprints")
        if isinstance(nested, dict):
            return str(nested.get("settings") or "").strip()
        return ""

    @staticmethod
    def _entry_env_fp(entry: Dict[str, Any]) -> str:
        if str(entry.get("env_fp") or "").strip():
            return str(entry.get("env_fp") or "").strip()
        nested = entry.get("fingerprints")
        if isinstance(nested, dict):
            return str(nested.get("env") or "").strip()
        return ""

    @classmethod
    def get_registry_entry(
        cls,
        simulations_root: Path,
        version_id: str,
    ) -> Optional[Dict[str, Any]]:
        vid = str(version_id or "").strip()
        if not vid:
            return None
        entry = cls._registry(cls.read_root_meta(simulations_root)).get(vid)
        return dict(entry) if isinstance(entry, dict) else None

    @classmethod
    def list_version_ids(cls, simulations_root: Path) -> List[str]:
        root = Path(simulations_root)
        meta_ids = [
            vid
            for vid in cls._registry(cls.read_root_meta(root))
            if str(vid).strip().isdigit()
        ]
        disk_ids = [
            p.name
            for p in root.iterdir()
            if p.is_dir() and p.name.isdigit()
        ] if root.is_dir() else []
        seen: set[str] = set()
        out: List[str] = []
        for vid in sorted(set(meta_ids + disk_ids), key=int):
            if vid not in seen:
                seen.add(vid)
                out.append(vid)
        return out

    @classmethod
    def ensure_registry_entry(
        cls,
        simulations_root: Path,
        version_id: str,
    ) -> Dict[str, Any]:
        vid = str(version_id or "").strip()
        root_meta = cls.read_root_meta(simulations_root)
        registry = cls._registry(root_meta)
        existing = registry.get(vid)
        if isinstance(existing, dict) and existing:
            return dict(existing)
        entry = {
            "created_at": datetime.now().isoformat(),
            "settings_fp": "",
            "env_fp": "",
        }
        registry[vid] = entry
        root_meta["registry"] = registry
        root_meta.pop("fingerprint_index", None)
        cls.write_root_meta(simulations_root, root_meta)
        return entry

    @classmethod
    def register_version(
        cls,
        simulations_root: Path,
        version_id: str,
        *,
        settings_fp: str,
        env_fp: str,
    ) -> None:
        vid = str(version_id or "").strip()
        root_meta = cls.read_root_meta(simulations_root)
        registry = cls._registry(root_meta)
        entry = dict(registry.get(vid) or {})
        if not entry:
            entry = cls.ensure_registry_entry(simulations_root, vid)
            root_meta = cls.read_root_meta(simulations_root)
            registry = cls._registry(root_meta)

        sfp = str(settings_fp or "").strip()
        efp = str(env_fp or "").strip()
        entry.setdefault("created_at", datetime.now().isoformat())
        if sfp:
            entry["settings_fp"] = sfp
        if efp:
            entry["env_fp"] = efp
        entry.pop("fingerprints", None)
        entry["updated_at"] = datetime.now().isoformat()
        registry[vid] = entry
        root_meta["registry"] = registry
        root_meta.pop("fingerprint_index", None)
        cls.write_root_meta(simulations_root, root_meta)

    @classmethod
    def find_version_by_fingerprints(
        cls,
        simulations_root: Path,
        settings_fp: str,
        env_fp: str,
    ) -> Optional[str]:
        sfp = str(settings_fp or "").strip()
        efp = str(env_fp or "").strip()
        if not sfp or not efp:
            return None
        root = Path(simulations_root)
        if not root.is_dir():
            return None

        root_meta = cls.read_root_meta(root)
        for vid in sorted(cls._registry(root_meta), key=lambda x: int(x)):
            entry = cls._registry(root_meta).get(vid)
            if not isinstance(entry, dict):
                continue
            if (
                cls._entry_settings_fp(entry) == sfp
                and cls._entry_env_fp(entry) == efp
            ):
                return str(vid).strip()
        return None

    @classmethod
    def resolve_version(
        cls,
        simulations_root: Path,
        version_id: str,
    ) -> Optional[Dict[str, Any]]:
        vid = str(version_id or "").strip()
        if not vid:
            return None
        entry = cls.get_registry_entry(simulations_root, vid)
        if entry is not None:
            return entry
        version_dir = Path(simulations_root) / vid
        if version_dir.is_dir():
            return {"settings_fp": "", "env_fp": ""}
        return None

    @classmethod
    def step_has_artifacts(
        cls,
        simulations_root: Path,
        version_id: str,
        kind: SimulateKind,
    ) -> bool:
        step_dir = _STEP_DIRS.get(kind, "")
        path = Path(simulations_root) / str(version_id).strip() / step_dir
        return path.is_dir() and (path / RUNTIME_ENV_FILE).is_file()

    @classmethod
    def step_status(
        cls,
        simulations_root: Path,
        version_id: str,
        kind: SimulateKind,
    ) -> str:
        return (
            "ok"
            if cls.step_has_artifacts(simulations_root, version_id, kind)
            else "missing"
        )

    @classmethod
    def find_version_by_settings_fp(
        cls,
        simulations_root: Path,
        settings_fp: str,
    ) -> Optional[str]:
        """按 ``settings_fp`` 扫 registry（不限 env）；用于环境失效提示。"""
        sfp = str(settings_fp or "").strip()
        if not sfp:
            return None
        root_meta = cls.read_root_meta(Path(simulations_root))
        for vid in sorted(cls._registry(root_meta), key=lambda x: int(x)):
            entry = cls._registry(root_meta).get(vid)
            if not isinstance(entry, dict):
                continue
            if cls._entry_settings_fp(entry) == sfp:
                return str(vid).strip()
        return None

    @classmethod
    def is_env_invalid(
        cls,
        entry: Optional[Dict[str, Any]],
        current_env_fp: str,
    ) -> bool:
        """registry ``env_fp`` 与当前运行环境指纹不一致 → 环境失效。"""
        if not isinstance(entry, dict) or not entry:
            return False
        stored = cls._entry_env_fp(entry)
        current = str(current_env_fp or "").strip()
        if not stored or not current:
            return False
        return stored != current

    @classmethod
    def env_invalid_for_version(
        cls,
        simulations_root: Path,
        version_id: str,
        current_env_fp: str,
    ) -> bool:
        entry = cls.get_registry_entry(simulations_root, version_id)
        return cls.is_env_invalid(entry, current_env_fp)

    @classmethod
    def remove_version_from_registry(
        cls,
        simulations_root: Path,
        version_id: str,
    ) -> None:
        vid = str(version_id or "").strip()
        root_meta = cls.read_root_meta(simulations_root)
        registry = cls._registry(root_meta)
        registry.pop(vid, None)
        root_meta["registry"] = registry
        root_meta.pop("fingerprint_index", None)
        cls.write_root_meta(simulations_root, root_meta)


__all__ = ["VersionMetaStore"]
