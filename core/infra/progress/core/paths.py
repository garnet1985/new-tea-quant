"""Progress directory resolution (tree + channel 共用根目录)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from core.infra.progress.core import progress_constants as _c


def resolve_progress_directory() -> Path:
    raw = os.environ.get(_c.ENV_PROGRESS_DIR, "").strip()
    if raw:
        return Path(raw)
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return Path(tempfile.gettempdir()) / _c.PYTEST_PROGRESS_SUBDIR
    try:
        from core.infra.project_context import ProjectContext

        return (
            ProjectContext.path.get_userspace_tmp_directory()
            / _c.USERSPACE_PROGRESS_SEGMENT
        )
    except Exception:
        return Path(tempfile.gettempdir()) / _c.FALLBACK_PROGRESS_SUBDIR


__all__ = ["resolve_progress_directory"]