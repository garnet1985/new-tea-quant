"""Shared atomic JSON write + ISO timestamps for pipeline stores."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def runtime_dir() -> Path:
    from core.infra.project_context import ProjectContext

    return ProjectContext.path.get_userspace_ntq_directory() / "runtime"


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as tmp:
        tmp.write(json.dumps(payload, ensure_ascii=False, indent=2))
        tmp_path = Path(tmp.name)
    os.replace(str(tmp_path), str(path))
