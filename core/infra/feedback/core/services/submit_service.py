"""Build and POST soft-feedback payloads. No Trace.consent gate."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional

from ..defaults import FeedbackDefaults
from .client_service import FeedbackClientService

logger = logging.getLogger(__name__)

_ALLOWED_RATINGS = frozenset({"up", "down"})


class FeedbackSubmitService:
    """Submit one feedback event. Never raises to callers via facade."""

    @staticmethod
    def submit(
        *,
        rating: str,
        text: str = "",
        source: str = "popup",
        meta: Optional[Mapping[str, Any]] = None,
    ) -> bool:
        try:
            if os.environ.get("NTQ_FEEDBACK_SKIP", "").strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }:
                return False

            rating_clean = str(rating or "").strip().lower()
            if rating_clean not in _ALLOWED_RATINGS:
                return False

            text_clean = FeedbackSubmitService._clip_text(text)
            source_clean = FeedbackSubmitService._safe_source(source)

            install_id = FeedbackSubmitService._installation_id()
            if not install_id:
                return False

            payload: Dict[str, Any] = {
                "event_id": str(uuid.uuid4()),
                "installation_id": install_id,
                "occurred_at": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "rating": rating_clean,
                "source": source_clean,
                "meta": FeedbackSubmitService._build_meta(meta),
            }
            if text_clean:
                payload["text"] = text_clean

            url = FeedbackSubmitService._target_url()
            timeout = FeedbackSubmitService._timeout_sec()
            return FeedbackClientService.post(url, payload, timeout_sec=timeout)
        except Exception as exc:
            logger.debug("feedback submit failed: %s", exc)
            return False

    @staticmethod
    def _installation_id() -> Optional[str]:
        try:
            from core.infra.trace.core.services.identity_service import (
                TraceIdentityService,
            )

            return TraceIdentityService.get_or_create()
        except Exception as exc:
            logger.debug("installation_id unavailable: %s", exc)
            return None

    @staticmethod
    def _target_url() -> str:
        env = (os.environ.get("NTQ_FEEDBACK_ENDPOINT") or "").strip()
        return env or FeedbackDefaults.TARGET_URL

    @staticmethod
    def _timeout_sec() -> float:
        raw = (os.environ.get("NTQ_FEEDBACK_TIMEOUT") or "").strip()
        if raw:
            try:
                return max(0.5, float(raw))
            except ValueError:
                pass
        return float(FeedbackDefaults.TIMEOUT_SEC)

    @staticmethod
    def _clip_text(text: Any) -> str:
        if text is None:
            return ""
        s = str(text).strip()
        if not s:
            return ""
        max_n = int(FeedbackDefaults.MAX_TEXT_CODEPOINTS)
        if len(s) > max_n:
            return s[:max_n]
        return s

    @staticmethod
    def _safe_source(source: Any) -> str:
        s = str(source or "popup").strip()[:32] or "popup"
        out = []
        for ch in s:
            if ch.isalnum() or ch in "._-":
                out.append(ch)
        return "".join(out) or "popup"

    @staticmethod
    def _build_meta(extra: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
        meta: Dict[str, Any] = {}
        try:
            from core.infra.project_context import ProjectContext

            ver = ProjectContext.meta.core_version()
            if ver:
                meta["ntq_version"] = str(ver)[:32]
        except Exception:
            pass
        if isinstance(extra, Mapping):
            for key, value in list(extra.items())[:16]:
                if not isinstance(key, str) or not key or len(key) > 64:
                    continue
                kl = key.lower()
                if kl in {
                    "ip",
                    "hostname",
                    "username",
                    "password",
                    "token",
                    "secret",
                    "authorization",
                }:
                    continue
                if isinstance(value, (bool, int)):
                    meta[key] = value
                elif isinstance(value, float):
                    if value == value and abs(value) != float("inf"):
                        meta[key] = value
                elif isinstance(value, str):
                    t = value.strip()
                    if t:
                        meta[key] = t[:256]
        return meta
