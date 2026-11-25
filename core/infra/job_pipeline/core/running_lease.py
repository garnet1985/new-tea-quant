"""JobPipeline running 槽租约：acquire / release。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.infra.job_pipeline.core import registry_store


class RunningLease:
    """``acquire`` / ``release`` / context manager。"""

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
        self.snapshot: Optional[Dict[str, Any]] = None

    def acquire(self) -> Dict[str, Any]:
        snap = registry_store.acquire_running(
            {
                "kind": self.kind,
                "job_id": self.job_id,
                "resource_key": self.resource_key,
                "label": self.label,
                "domains": self.domains,
            }
        )
        self._held = True
        self.snapshot = snap
        return snap

    def release(self) -> None:
        if not self._held:
            return
        registry_store.release_running(self.job_id)
        self._held = False

    def __enter__(self) -> "RunningLease":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
