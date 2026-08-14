"""Payload sanitizers for event / meta / body."""

from __future__ import annotations

import json
import platform
from typing import Any, Dict, Mapping, Optional

_MAX_STRING_LEN = 256
_MAX_EVENT_NAME_LEN = 64
_MAX_BODY_DEPTH = 3
_MAX_BODY_KEYS = 40

_BLOCKED_BODY_KEYS = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "authorization",
        "cookie",
        "private_key",
        "access_token",
        "refresh_token",
    }
)


class TraceSanitizeService:
    """Validate event names and scrub meta / body before enqueue."""

    @staticmethod
    def event_name(event_name: str) -> Optional[str]:
        if not isinstance(event_name, str):
            return None
        name = event_name.strip()
        if not name or len(name) > _MAX_EVENT_NAME_LEN:
            return None
        for ch in name:
            if not (ch.isalnum() or ch in "._-"):
                return None
        return name

    @staticmethod
    def build_client_meta(*, ntq_version: str = "") -> Dict[str, Any]:
        meta: Dict[str, Any] = {
            "os": (platform.system() or "unknown").lower(),
            "python_version": platform.python_version(),
            "arch": platform.machine() or "",
        }
        cpu_cores = TraceSanitizeService._cpu_cores()
        if cpu_cores is not None:
            meta["cpu_cores"] = cpu_cores
        memory_mb = TraceSanitizeService._memory_mb()
        if memory_mb is not None:
            meta["memory_mb"] = memory_mb
        db = TraceSanitizeService._database_type()
        if db:
            meta["db"] = db
        disk = TraceSanitizeService._disk_type()
        if disk:
            meta["disk_type"] = disk
        if ntq_version:
            meta["ntq_version"] = str(ntq_version)[:32]
        return meta

    @staticmethod
    def _cpu_cores() -> Optional[int]:
        try:
            from core.infra.machine_capacity import MachineInfo

            return max(1, int(MachineInfo.get_cpu_count()))
        except Exception:
            try:
                import os

                n = os.cpu_count()
                return max(1, int(n)) if n else None
            except Exception:
                return None

    @staticmethod
    def _memory_mb() -> Optional[int]:
        try:
            from core.infra.machine_capacity import MachineInfo

            total_mb, _available = MachineInfo.virtual_memory_mb()
            if total_mb is None:
                return None
            return max(1, int(round(float(total_mb))))
        except Exception:
            return None

    @staticmethod
    def _database_type() -> Optional[str]:
        try:
            from core.infra.project_context import ProjectContext

            raw = str(ProjectContext.config.get_database_type() or "").strip().lower()
            if raw in {"duckdb", "mysql", "postgresql"}:
                return raw
            if raw in {"pgsql", "postgres"}:
                return "postgresql"
            return "unknown" if raw else None
        except Exception:
            return None

    @staticmethod
    def _disk_type() -> Optional[str]:
        try:
            from core.infra.machine_capacity import MachineInfo
            from core.infra.project_context import ProjectContext

            root = ProjectContext.path.get_userspace_root()
            kind = str(MachineInfo.get_disk_type(root) or "").strip().lower()
            if kind in {"ssd", "hdd", "unknown"}:
                return kind
            return "unknown"
        except Exception:
            try:
                from core.infra.machine_capacity import MachineInfo

                kind = str(MachineInfo.get_disk_type() or "").strip().lower()
                return kind if kind in {"ssd", "hdd", "unknown"} else "unknown"
            except Exception:
                return None

    @staticmethod
    def body(
        body: Optional[Mapping[str, Any]],
        *,
        max_bytes: int = 4096,
    ) -> Dict[str, Any]:
        if not body:
            return {}
        cleaned = TraceSanitizeService._jsonish(body, depth=0)
        if not isinstance(cleaned, dict):
            return {}
        return TraceSanitizeService._cap_bytes(cleaned, max_bytes=max_bytes)

    @staticmethod
    def meta(meta: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
        if not meta:
            return {}
        out: Dict[str, Any] = {}
        for key, value in meta.items():
            if not isinstance(key, str) or not key or len(key) > 64:
                continue
            if key.lower() in _BLOCKED_BODY_KEYS or key.lower() in {
                "ip",
                "hostname",
                "username",
            }:
                continue
            cleaned = TraceSanitizeService._scalar(value)
            if cleaned is not None:
                out[key] = cleaned
        return out

    @staticmethod
    def _jsonish(value: Any, *, depth: int) -> Any:
        if depth > _MAX_BODY_DEPTH:
            return None
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and not isinstance(value, bool):
            return int(value)
        if isinstance(value, float):
            if value != value or value in (float("inf"), float("-inf")):
                return None
            return float(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            return text[:_MAX_STRING_LEN]
        if isinstance(value, Mapping):
            out: Dict[str, Any] = {}
            for i, (key, child) in enumerate(value.items()):
                if i >= _MAX_BODY_KEYS:
                    break
                if not isinstance(key, str) or not key or len(key) > 64:
                    continue
                if key.lower() in _BLOCKED_BODY_KEYS:
                    continue
                cleaned = TraceSanitizeService._jsonish(child, depth=depth + 1)
                if cleaned is not None:
                    out[key] = cleaned
            return out
        if isinstance(value, (list, tuple)):
            items = []
            for child in list(value)[:20]:
                cleaned = TraceSanitizeService._jsonish(child, depth=depth + 1)
                if cleaned is not None:
                    items.append(cleaned)
            return items
        return None

    @staticmethod
    def _scalar(value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and not isinstance(value, bool):
            return int(value)
        if isinstance(value, float):
            if value != value or value in (float("inf"), float("-inf")):
                return None
            return float(value)
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            return text[:_MAX_STRING_LEN]
        return None

    @staticmethod
    def _cap_bytes(data: Dict[str, Any], *, max_bytes: int) -> Dict[str, Any]:
        raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        if len(raw.encode("utf-8")) <= max_bytes:
            return data
        out = dict(data)
        for key in sorted(out.keys(), reverse=True):
            out.pop(key, None)
            raw = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
            if len(raw.encode("utf-8")) <= max_bytes:
                break
        return out
