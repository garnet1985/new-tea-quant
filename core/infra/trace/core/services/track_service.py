"""Track / queue orchestration: sanitize → TraceEvent → POST or local queue."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from ...contracts import TraceEvent
from .client_service import TraceClientService
from .config_service import TraceConfigService
from .identity_service import TraceIdentityService
from .queue_service import TraceQueueService
from .sanitize_service import TraceSanitizeService


class TraceTrackService:
    """Build usage events; ``track`` POSTs immediately, ``queue`` enqueues only."""

    @staticmethod
    def track(event: str, body: Optional[Mapping[str, Any]] = None) -> None:
        """Build one event and POST immediately; on failure enqueue for retry."""
        try:
            cfg = TraceConfigService.load()
            if not cfg.enabled:
                return
            built = TraceTrackService._build_event(event, body, cfg=cfg)
            if built is None:
                return
            url = str(cfg.target_url or "")
            timeout = float(cfg.timeout_sec or 2.0)
            if url and TraceClientService.post(url, built, timeout_sec=timeout):
                return
            TraceQueueService.enqueue(built, queue_max=cfg.queue_max)
        except Exception:
            return

    @staticmethod
    def queue(event: str, body: Optional[Mapping[str, Any]] = None) -> None:
        """Build one event and enqueue locally (no network I/O)."""
        try:
            cfg = TraceConfigService.load()
            if not cfg.enabled:
                return
            built = TraceTrackService._build_event(event, body, cfg=cfg)
            if built is None:
                return
            TraceQueueService.enqueue(built, queue_max=cfg.queue_max)
        except Exception:
            return

    @staticmethod
    def _build_event(
        event: str,
        body: Optional[Mapping[str, Any]],
        *,
        cfg: Any,
    ) -> Optional[TraceEvent]:
        name = TraceSanitizeService.event_name(event)
        if name is None:
            return None

        body_clean = TraceSanitizeService.body(body, max_bytes=cfg.body_max_bytes)
        install_id = TraceIdentityService.get_or_create()
        if not install_id:
            return None

        ntq_version = ""
        try:
            from core.infra.project_context import ProjectContext

            ver = ProjectContext.meta.core_version()
            ntq_version = str(ver) if ver else ""
        except Exception:
            pass

        meta = TraceSanitizeService.meta(
            TraceSanitizeService.build_client_meta(ntq_version=ntq_version)
        )
        return TraceEvent(
            schema_version=2,
            event_id=str(uuid.uuid4()),
            installation_id=install_id,
            event=name,
            occurred_at=datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            meta=meta,
            body=body_clean,
            attempts=0,
        )
