"""User consent for sharing anonymous debug data (opt-in)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ...contracts import TraceConsent

logger = logging.getLogger(__name__)

_CONSENT_FILENAME = "trace_consent.json"


class TraceConsentService:
    """
    Persist the user's opt-in decision.

    Stored in ``userspace/system/config/trace_consent.json`` (survives
    ``.ntq`` cache cleanup). Missing file means "not asked yet" → no tracking.
    """

    @staticmethod
    def read() -> TraceConsent:
        path = TraceConsentService.consent_path()
        if path is None or not path.is_file():
            return TraceConsent()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.debug("trace consent read failed: %s", exc)
            return TraceConsent()
        if not isinstance(raw, dict):
            return TraceConsent()
        enabled = bool(raw.get("enabled", False))
        return TraceConsent(
            decided=True,
            enabled=enabled,
            decided_at=str(raw.get("decided_at") or ""),
            source=str(raw.get("source") or ""),
        )

    @staticmethod
    def is_decided() -> bool:
        return TraceConsentService.read().decided

    @staticmethod
    def is_granted() -> bool:
        consent = TraceConsentService.read()
        return consent.decided and consent.enabled

    @staticmethod
    def grant(*, source: str = "") -> bool:
        return TraceConsentService.set(True, source=source)

    @staticmethod
    def revoke(*, source: str = "") -> bool:
        return TraceConsentService.set(False, source=source)

    @staticmethod
    def set(enabled: bool, *, source: str = "") -> bool:
        """Write the decision. Revoking also drops any pending queued events."""
        path = TraceConsentService.consent_path()
        if path is None:
            return False
        payload = {
            "enabled": bool(enabled),
            "decided_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "source": str(source or "")[:32],
        }
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            tmp.replace(path)
        except Exception as exc:
            logger.debug("trace consent write failed: %s", exc)
            return False

        try:
            from .track_service import TraceTrackService

            TraceTrackService.track_decision(
                enabled=bool(enabled),
                source=str(source or ""),
            )
        except Exception as exc:
            logger.debug("track.decision emit failed: %s", exc)

        if not enabled:
            try:
                from .queue_service import TraceQueueService

                TraceQueueService.purge()
            except Exception as exc:
                logger.debug("queue purge after revoke failed: %s", exc)
        return True

    @staticmethod
    def consent_path() -> Optional[Path]:
        try:
            from core.infra.project_context import ProjectContext

            return ProjectContext.path.get_user_config_root() / _CONSENT_FILENAME
        except Exception as exc:
            logger.debug("consent path unavailable: %s", exc)
            return None
