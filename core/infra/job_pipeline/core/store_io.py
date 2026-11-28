"""Shared atomic JSON write + ISO timestamps for pipeline stores."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from core.infra.utils import Utils


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def runtime_dir() -> Path:
    from core.infra.project_context import ProjectContext

    return ProjectContext.path.get_userspace_ntq_directory() / "runtime"


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    Utils.io.atomic_write_json(path, payload)
