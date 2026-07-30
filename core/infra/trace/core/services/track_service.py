"""Track orchestration: sanitize → TraceEvent → local queue."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from ...contracts import TraceEvent
from .config_service import TraceConfigService
from .identity_service import TraceIdentityService
from .queue_service import TraceQueueService
from .sanitize_service import TraceSanitizeService


class TraceTrackService:
    """Build and enqueue one usage event. Never raises; no network I/O."""

    @staticmethod
    def track(event: str, body: Optional[Mapping[str, Any]] = None) -> None:
        try:
            cfg = TraceConfigService.load()
            if not cfg.enabled:
                return
            name = TraceSanitizeService.event_name(event)
            if name is None:
                return

            body_clean = TraceSanitizeService.body(body, max_bytes=cfg.body_max_bytes)
            install_id = TraceIdentityService.get_or_create()
            if not install_id:
                return

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
            trace_event = TraceEvent(
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
            TraceQueueService.enqueue(trace_event, queue_max=cfg.queue_max)
        except Exception:
            return
