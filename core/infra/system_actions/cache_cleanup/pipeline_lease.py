"""Global DuckDB pipeline lease (single active long-running job)."""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List, Optional

from core.infra.project_context import ProjectContext
from core.infra.system_actions.contracts import (
    VALID_KINDS,
    PipelineLeaseBusyError,
)

_LOCK = threading.Lock()


def _lease_path() -> Path:
    return ProjectContext.path.get_userspace_ntq_directory() / "runtime" / "pipeline_active.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, payload: Dict[str, Any]) -> None:
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


class PipelineLease:
    """Context manager: acquire on enter, release on exit."""

    @staticmethod
    def read_status() -> Dict[str, Any]:
        """Return idle or active lease snapshot for ``GET /runtime/pipeline``."""
        with _LOCK:
            path = _lease_path()
            if not path.is_file():
                return PipelineLease._idle_message()
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return PipelineLease._idle_message()
            if not isinstance(raw, dict) or not raw.get("job_id"):
                return PipelineLease._idle_message()
            return {
                "busy": True,
                "kind": raw.get("kind"),
                "job_id": raw.get("job_id"),
                "resource_key": raw.get("resource_key"),
                "label": raw.get("label"),
                "domains": list(raw.get("domains") or []),
                "started_at": raw.get("started_at"),
            }

    @staticmethod
    def _idle_message() -> Dict[str, Any]:
        return {
            "busy": False,
            "kind": None,
            "job_id": None,
            "resource_key": None,
            "label": None,
            "domains": [],
            "started_at": None,
        }

    def __init__(
        self,
        *,
        kind: str,
        job_id: str,
        resource_key: str = "",
        label: str = "",
        domains: Optional[List[str]] = None,
    ) -> None:
        self.kind = str(kind or "").strip()
        self.job_id = str(job_id or "").strip()
        self.resource_key = str(resource_key or "").strip()
        self.label = str(label or "").strip()
        self.domains = list(domains or [])
        self._held = False

    def acquire(self) -> None:
        if self.kind not in VALID_KINDS:
            raise ValueError(f"invalid pipeline kind: {self.kind!r}")
        if not self.job_id:
            raise ValueError("job_id required for pipeline lease")

        with _LOCK:
            path = _lease_path()
            if path.is_file():
                try:
                    existing = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    existing = {}
                if isinstance(existing, dict) and existing.get("job_id"):
                    raise PipelineLeaseBusyError(existing)

            payload = {
                "kind": self.kind,
                "job_id": self.job_id,
                "resource_key": self.resource_key,
                "label": self.label or self.resource_key or self.kind,
                "domains": self.domains,
                "started_at": _iso_now(),
            }
            _atomic_write(path, payload)
            self._held = True

    def release(self) -> None:
        with _LOCK:
            path = _lease_path()
            if not self._held:
                return
            if path.is_file():
                try:
                    raw = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    raw = {}
                if isinstance(raw, dict) and str(raw.get("job_id") or "") == self.job_id:
                    path.unlink(missing_ok=True)
            self._held = False

    def __enter__(self) -> "PipelineLease":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
