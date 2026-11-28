"""Track / queue orchestration: sanitize → TraceEvent → POST or local queue."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from ...contracts import TraceEvent
from .client_service import TraceClientService
from .config_service import TraceConfigService
from .endpoint_service import TraceEndpointService
from .identity_service import TraceIdentityService
from .queue_service import TraceQueueService
from .sanitize_service import TraceSanitizeService


class TraceTrackService:
    """Build usage events; ``track`` POSTs immediately, ``queue`` enqueues only."""

    _DECISION_EVENT = "track.decision"
    _MEMBER_BIND_EVENT = "member.bind"

    @staticmethod
    def track(event: str, body: Optional[Mapping[str, Any]] = None) -> None:
        """Build one event and POST immediately; on failure enqueue for retry."""
        try:
            cfg = TraceConfigService.load()
            if not cfg.enabled or not str(cfg.target_url or "").strip():
                return
            TraceTrackService._emit(event, body, cfg=cfg, enqueue_on_fail=True)
        except Exception:
            return

    @staticmethod
    def track_setup(event: str, body: Optional[Mapping[str, Any]] = None) -> None:
        """安装事件。只有发送端声明可以跳过同意时才发。"""
        try:
            if TraceConfigService.should_skip():
                return
            if not TraceEndpointService.setup_without_consent():
                return
            cfg = TraceConfigService.load()
            if not str(cfg.target_url or "").strip():
                return
            TraceTrackService._emit(event, body, cfg=cfg, enqueue_on_fail=True)
        except Exception:
            return

    @staticmethod
    def queue(event: str, body: Optional[Mapping[str, Any]] = None) -> None:
        """Build one event and enqueue locally (no network I/O)."""
        try:
            cfg = TraceConfigService.load()
            if not cfg.enabled or not str(cfg.target_url or "").strip():
                return
            built = TraceTrackService._build_event(event, body, cfg=cfg)
            if built is None:
                return
            TraceQueueService.enqueue(built, queue_max=cfg.queue_max)
        except Exception:
            return

    @staticmethod
    def track_decision(*, enabled: bool, source: str = "") -> None:
        """
        Report a consent decision.

        Bypasses ``consent.enabled`` so denials are still visible; still respects
        ``NTQ_TRACE_SKIP``. On POST failure, enqueues only when ``enabled`` is True
        (revoke purges the queue immediately after).
        """
        try:
            if TraceConfigService.should_skip():
                return
            cfg = TraceConfigService.load()
            body = {
                "enabled": bool(enabled),
                "source": str(source or "")[:32],
            }
            TraceTrackService._emit(
                TraceTrackService._DECISION_EVENT,
                body,
                cfg=cfg,
                enqueue_on_fail=bool(enabled),
            )
        except Exception:
            return

    @staticmethod
    def track_member_bind(*, source: str = "", force: bool = False) -> None:
        """
        Link this installation to the mapped membership token.

        Bypasses usage-consent: mapping a member credential is an explicit
        identity signal. Still respects ``NTQ_TRACE_SKIP``. Without ``force``,
        skips when a local marker already matches the current installation_id.
        """
        try:
            if TraceConfigService.should_skip():
                return
            from core.infra.membership import Membership

            if not Membership.read():
                return
            cfg = TraceConfigService.load()
            if not str(cfg.target_url or "").strip():
                return
            install_id = TraceIdentityService.get_or_create()
            if not install_id:
                return
            if not force and TraceTrackService._member_bind_done(install_id):
                return
            TraceTrackService._emit(
                TraceTrackService._MEMBER_BIND_EVENT,
                {"source": str(source or "")[:32]},
                cfg=cfg,
                enqueue_on_fail=True,
            )
            TraceTrackService._mark_member_bind(install_id)
        except Exception:
            return

    @staticmethod
    def _member_bind_marker_path() -> Path:
        from core.infra.project_context import ProjectContext

        return ProjectContext.path.get_user_prefs_root() / "trace_member_bind.json"

    @staticmethod
    def _member_bind_done(install_id: str) -> bool:
        path = TraceTrackService._member_bind_marker_path()
        if not path.is_file():
            return False
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return False
        if not isinstance(raw, dict):
            return False
        return str(raw.get("installation_id") or "") == str(install_id)

    @staticmethod
    def _mark_member_bind(install_id: str) -> None:
        path = TraceTrackService._member_bind_marker_path()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "installation_id": str(install_id),
                "bound_at": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            }
            path.write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
                + "\n",
                encoding="utf-8",
            )
        except Exception:
            return

    @staticmethod
    def _emit(
        event: str,
        body: Optional[Mapping[str, Any]],
        *,
        cfg: Any,
        enqueue_on_fail: bool,
    ) -> None:
        built = TraceTrackService._build_event(event, body, cfg=cfg)
        if built is None:
            return
        url = str(cfg.target_url or "")
        timeout = float(cfg.timeout_sec or 2.0)
        if url and TraceClientService.post(url, built, timeout_sec=timeout):
            return
        if enqueue_on_fail:
            TraceQueueService.enqueue(built, queue_max=cfg.queue_max)

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
