"""Anonymous installation identity for NTQ trace."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

_ID_PREFIX = "ntq_i_"


class TraceIdentityService:
    """Persist and return anonymous installation_id under userspace/.ntq/trace/."""

    @staticmethod
    def get_or_create() -> str | None:
        path = TraceIdentityService._id_path()
        if path is None:
            return None
        try:
            if path.is_file():
                existing = path.read_text(encoding="utf-8").strip()
                if existing.startswith(_ID_PREFIX) and len(existing) > len(_ID_PREFIX) + 8:
                    return existing
            new_id = f"{_ID_PREFIX}{uuid.uuid4().hex}"
            path.write_text(new_id + "\n", encoding="utf-8")
            return new_id
        except Exception as exc:
            logger.debug("installation_id read/write failed: %s", exc)
            return None

    @staticmethod
    def _trace_root() -> Path | None:
        try:
            from core.infra.project_context import ProjectContext

            root = ProjectContext.path.get_userspace_ntq_directory() / "trace"
            root.mkdir(parents=True, exist_ok=True)
            return root
        except Exception as exc:
            logger.debug("trace root unavailable: %s", exc)
            return None

    @staticmethod
    def _id_path() -> Path | None:
        root = TraceIdentityService._trace_root()
        return None if root is None else root / "installation_id"
