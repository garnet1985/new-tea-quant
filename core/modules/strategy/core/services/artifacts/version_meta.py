"""仿真 version 注册表：仅 ``simulations/meta.json``。

根 meta 职责（索引层）:
- ``next_version_id``
- ``registry``：``{ vid: { created_at, execute_fp, env_fp, steps, ... } }``

``{vid}/`` 归档（三步共享，只写一次）:
- ``settings.json``：当时完整运行 settings
- ``effective_settings.json``：白名单投影
- ``scope.json``：标的快照 + 解析后的回测区间
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts.consts import (
    EFFECTIVE_SETTINGS_FILE,
    RUNTIME_ENV_FILE,
    SCOPE_FILE,
    SETTINGS_FILE,
)
from core.system import get_version

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
    """读写 ``simulations/meta.json`` registry 与 ``{vid}/`` 归档文件。"""

    @staticmethod
    def root_meta_path(simulations_root: Path) -> Path:
        return Path(simulations_root) / _ROOT_META

    @staticmethod
    def version_dir(simulations_root: Path, version_id: str) -> Path:
        return Path(simulations_root) / str(version_id).strip()

    @classmethod
    def effective_settings_path(cls, simulations_root: Path, version_id: str) -> Path:
        return cls.version_dir(simulations_root, version_id) / EFFECTIVE_SETTINGS_FILE

    @classmethod
    def settings_path(cls, simulations_root: Path, version_id: str) -> Path:
        return cls.version_dir(simulations_root, version_id) / SETTINGS_FILE

    @classmethod
    def scope_path(cls, simulations_root: Path, version_id: str) -> Path:
        return cls.version_dir(simulations_root, version_id) / SCOPE_FILE

    @classmethod
    def read_root_meta(cls, simulations_root: Path) -> Dict[str, Any]:
        return read_json(cls.root_meta_path(simulations_root))

    @classmethod
    def write_root_meta(
        cls, simulations_root: Path, payload: Dict[str, Any]
    ) -> None:
        write_json(cls.root_meta_path(simulations_root), payload)

    @classmethod
    def read_settings(
        cls,
        simulations_root: Path,
        version_id: str,
    ) -> Optional[Dict[str, Any]]:
        payload = read_json(cls.settings_path(simulations_root, version_id))
        return dict(payload) if payload else None

    @classmethod
    def write_settings(
        cls,
        simulations_root: Path,
        version_id: str,
        settings: Dict[str, Any],
    ) -> Path:
        vid = str(version_id or "").strip()
        path = cls.settings_path(simulations_root, vid)
        if path.is_file():
            return path
        write_json(path, dict(settings or {}))
        return path

    @classmethod
    def read_effective_settings(
        cls,
        simulations_root: Path,
        version_id: str,
    ) -> Optional[Dict[str, Any]]:
        payload = read_json(
            cls.effective_settings_path(simulations_root, version_id)
        )
        if not payload:
            return None
        payload.pop("entity_ids", None)
        return dict(payload)

    @classmethod
    def write_effective_settings(
        cls,
        simulations_root: Path,
        version_id: str,
        settings: Dict[str, Any],
    ) -> Path:
        vid = str(version_id or "").strip()
        path = cls.effective_settings_path(simulations_root, vid)
        if path.is_file():
            return path
        body = dict(settings or {})
        body.pop("entity_ids", None)
        write_json(path, body)
        return path

    @classmethod
    def read_scope(
        cls,
        simulations_root: Path,
        version_id: str,
    ) -> Optional[Dict[str, Any]]:
        payload = read_json(cls.scope_path(simulations_root, version_id))
        return dict(payload) if payload else None

    @classmethod
    def write_scope(
        cls,
        simulations_root: Path,
        version_id: str,
        *,
        entity_ids: Optional[Sequence[str]] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> Path:
        vid = str(version_id or "").strip()
        path = cls.scope_path(simulations_root, vid)
        if path.is_file():
            return path
        ids = [
            str(x).strip()
            for x in (entity_ids or [])
            if str(x).strip()
        ]
        write_json(
            path,
            {
                "entity_ids": sorted(ids),
                "start_date": str(start_date or "").strip(),
                "end_date": str(end_date or "").strip(),
            },
        )
        return path

    @classmethod
    def write_version_archive(
        cls,
        simulations_root: Path,
        version_id: str,
        *,
        full_settings: Dict[str, Any],
        effective_settings: Dict[str, Any],
        entity_ids: Optional[Sequence[str]] = None,
        start_date: str = "",
        end_date: str = "",
    ) -> None:
        """``{vid}/`` 身份归档；已有文件不覆盖。"""
        cls.write_settings(simulations_root, version_id, full_settings)
        cls.write_effective_settings(
            simulations_root, version_id, effective_settings
        )
        cls.write_scope(
            simulations_root,
            version_id,
            entity_ids=entity_ids,
            start_date=start_date,
            end_date=end_date,
        )

    @classmethod
    def read_archive_context(
        cls,
        simulations_root: Path,
        version_id: str,
    ) -> Dict[str, Any]:
        """``{vid}/`` 归档 + registry 指纹，供 step runtime hydrate。"""
        vid = str(version_id or "").strip()
        scope = cls.read_scope(simulations_root, vid) or {}
        entry = cls.get_registry_entry(simulations_root, vid) or {}
        effective = cls.read_effective_settings(simulations_root, vid) or {}
        ids = [
            str(x).strip()
            for x in (scope.get("entity_ids") or [])
            if str(x).strip()
        ]
        return {
            "entity_ids": ids,
            "start_date": str(scope.get("start_date") or "").strip(),
            "end_date": str(scope.get("end_date") or "").strip(),
            "effective_settings": dict(effective),
            "full_settings": cls.read_settings(simulations_root, vid) or {},
            "execute_fp": str(entry.get("execute_fp") or "").strip(),
            "env_fp": str(entry.get("env_fp") or "").strip(),
        }

    @classmethod
    def _registry(cls, root_meta: Dict[str, Any]) -> Dict[str, Any]:
        reg = root_meta.get("registry")
        return dict(reg) if isinstance(reg, dict) else {}

    @staticmethod
    def _entry_execute_fp(entry: Dict[str, Any]) -> str:
        return str(entry.get("execute_fp") or "").strip()

    @staticmethod
    def _entry_env_fp(entry: Dict[str, Any]) -> str:
        return str(entry.get("env_fp") or "").strip()

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
            "execute_fp": "",
            "env_fp": "",
            "engine_version": str(get_version() or ""),
            "steps": {},
        }
        registry[vid] = entry
        root_meta["registry"] = registry
        cls.write_root_meta(simulations_root, root_meta)
        return entry

    @classmethod
    def register_version(
        cls,
        simulations_root: Path,
        version_id: str,
        *,
        execute_fp: str,
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

        efp_execute = str(execute_fp or "").strip()
        efp_env = str(env_fp or "").strip()
        entry.setdefault("created_at", datetime.now().isoformat())
        if efp_execute:
            entry["execute_fp"] = efp_execute
        if efp_env:
            entry["env_fp"] = efp_env
        entry.setdefault("steps", {})
        entry.setdefault("engine_version", str(get_version() or ""))
        if not entry.get("engine_version"):
            entry["engine_version"] = str(get_version() or "")
        entry["updated_at"] = datetime.now().isoformat()
        registry[vid] = entry
        root_meta["registry"] = registry
        cls.write_root_meta(simulations_root, root_meta)

    @classmethod
    def mark_step_complete(
        cls,
        simulations_root: Path,
        version_id: str,
        kind: SimulateKind,
    ) -> None:
        vid = str(version_id or "").strip()
        if not vid:
            return
        root_meta = cls.read_root_meta(simulations_root)
        registry = cls._registry(root_meta)
        entry = dict(registry.get(vid) or {})
        if not entry:
            entry = cls.ensure_registry_entry(simulations_root, vid)
            root_meta = cls.read_root_meta(simulations_root)
            registry = cls._registry(root_meta)
        steps = dict(entry.get("steps") or {})
        steps[kind.value] = "ok"
        entry["steps"] = steps
        entry["updated_at"] = datetime.now().isoformat()
        registry[vid] = entry
        root_meta["registry"] = registry
        cls.write_root_meta(simulations_root, root_meta)

    @classmethod
    def find_version_by_fingerprints(
        cls,
        simulations_root: Path,
        execute_fp: str,
        env_fp: str,
    ) -> Optional[str]:
        execute = str(execute_fp or "").strip()
        efp = str(env_fp or "").strip()
        if not execute or not efp:
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
                cls._entry_execute_fp(entry) == execute
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
            return {"execute_fp": "", "env_fp": ""}
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
        entry = cls.get_registry_entry(simulations_root, version_id) or {}
        stored = (entry.get("steps") or {}).get(kind.value)
        if stored == "ok" or cls.step_has_artifacts(simulations_root, version_id, kind):
            return "ok"
        return "missing"

    @classmethod
    def find_version_by_execute_fp(
        cls,
        simulations_root: Path,
        execute_fp: str,
    ) -> Optional[str]:
        """按 ``execute_fp`` 扫 registry（不限 env）；用于环境失效提示。"""
        execute = str(execute_fp or "").strip()
        if not execute:
            return None
        root_meta = cls.read_root_meta(Path(simulations_root))
        for vid in sorted(cls._registry(root_meta), key=lambda x: int(x)):
            entry = cls._registry(root_meta).get(vid)
            if not isinstance(entry, dict):
                continue
            if cls._entry_execute_fp(entry) == execute:
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
        cls.write_root_meta(simulations_root, root_meta)


__all__ = ["VersionMetaStore"]
