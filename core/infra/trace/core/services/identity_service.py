"""Anonymous installation identity for NTQ trace."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

_ID_PREFIX = "ntq_i_"


class TraceIdentityService:
    """Anonymous installation_id: memory + repo ``.ntq``, then userspace when ready."""

    _cached_id: str | None = None

    @staticmethod
    def reset_cache() -> None:
        TraceIdentityService._cached_id = None

    @staticmethod
    def get_or_create() -> str | None:
        userspace = TraceIdentityService._read_id(TraceIdentityService._userspace_path())
        if userspace:
            TraceIdentityService._cached_id = userspace
            TraceIdentityService._persist(userspace)
            return TraceIdentityService._cached_id

        if TraceIdentityService._cached_id:
            TraceIdentityService._persist(TraceIdentityService._cached_id)
            return TraceIdentityService._cached_id

        staging = TraceIdentityService._read_id(TraceIdentityService._staging_path())
        if staging:
            TraceIdentityService._cached_id = staging
            TraceIdentityService._persist(staging)
            return TraceIdentityService._cached_id

        new_id = f"{_ID_PREFIX}{uuid.uuid4().hex}"
        TraceIdentityService._cached_id = new_id
        TraceIdentityService._persist(new_id)
        return TraceIdentityService._cached_id

    @staticmethod
    def _persist(install_id: str) -> None:
        if not TraceIdentityService._valid_id(install_id):
            return
        TraceIdentityService._write_id(TraceIdentityService._staging_path(), install_id)
        userspace_path = TraceIdentityService._userspace_path()
        existing = TraceIdentityService._read_id(userspace_path)
        if existing and existing != install_id:
            TraceIdentityService._cached_id = existing
            TraceIdentityService._write_id(TraceIdentityService._staging_path(), existing)
            return
        TraceIdentityService._write_id(userspace_path, install_id)

    @staticmethod
    def _valid_id(value: str) -> bool:
        text = str(value or "").strip()
        return text.startswith(_ID_PREFIX) and len(text) > len(_ID_PREFIX) + 8

    @staticmethod
    def _read_id(path: Path | None) -> str | None:
        if path is None or not path.is_file():
            return None
        try:
            existing = path.read_text(encoding="utf-8").strip()
        except Exception as exc:
            logger.debug("installation_id read failed: %s", exc)
            return None
        return existing if TraceIdentityService._valid_id(existing) else None

    @staticmethod
    def _write_id(path: Path | None, install_id: str) -> None:
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".id.tmp")
            tmp.write_text(install_id + "\n", encoding="utf-8")
            tmp.replace(path)
        except Exception as exc:
            logger.debug("installation_id write failed: %s", exc)

    @staticmethod
    def _userspace_path() -> Path | None:
        try:
            from core.infra.project_context import ProjectContext

            userspace_root = ProjectContext.path.get_userspace_root()
            if not userspace_root.is_dir():
                return None
            root = userspace_root / ".ntq" / "trace"
            root.mkdir(parents=True, exist_ok=True)
            return root / "installation_id"
        except Exception as exc:
            logger.debug("userspace installation_id path unavailable: %s", exc)
            return None

    @staticmethod
    def _staging_path() -> Path | None:
        try:
            from core.infra.project_context import ProjectContext

            root = ProjectContext.path.get_project_root() / ".ntq" / "trace"
            root.mkdir(parents=True, exist_ok=True)
            return root / "installation_id"
        except Exception as exc:
            logger.debug("staging installation_id path unavailable: %s", exc)
            return None
