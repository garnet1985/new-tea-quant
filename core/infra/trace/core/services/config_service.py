"""Trace configuration (module-internal defaults + consent + env overrides)."""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from ...contracts import TraceConfig
from .consent_service import TraceConsentService

# Module-internal defaults. Intentionally NOT exposed in core/default_config/,
# because tracing is opt-in and tunables are not user-facing knobs.
_DEFAULTS: Dict[str, Any] = {
    "target_url": "https://www.new-tea.cn/api/v1/traces",
    "timeout_sec": 2.0,
    "queue_max": 100,
    "extreme_depth": 20,
    "max_attempts": 10,
    "body_max_bytes": 4096,
    "bff_drain_interval_sec": 60,
}


class TraceConfigService:
    """Resolve TraceConfig; ``enabled`` comes from user consent (default off)."""

    @staticmethod
    def load() -> TraceConfig:
        return TraceConfig(
            enabled=TraceConfigService._resolve_enabled(),
            target_url=TraceConfigService._env_str("NTQ_TRACE_ENDPOINT")
            or str(_DEFAULTS["target_url"]),
            timeout_sec=TraceConfigService._env_float("NTQ_TRACE_TIMEOUT")
            or float(_DEFAULTS["timeout_sec"]),
            queue_max=int(_DEFAULTS["queue_max"]),
            extreme_depth=int(_DEFAULTS["extreme_depth"]),
            max_attempts=int(_DEFAULTS["max_attempts"]),
            body_max_bytes=int(_DEFAULTS["body_max_bytes"]),
            bff_drain_interval_sec=int(_DEFAULTS["bff_drain_interval_sec"]),
        )

    @staticmethod
    def is_enabled() -> bool:
        return bool(TraceConfigService.load().enabled)

    @staticmethod
    def as_dict() -> Dict[str, Any]:
        cfg = TraceConfigService.load()
        consent = TraceConsentService.read()
        return {
            "enabled": cfg.enabled,
            "consent_decided": consent.decided,
            "consent_enabled": consent.enabled,
            "target_url": cfg.target_url,
            "timeout_sec": cfg.timeout_sec,
            "queue_max": cfg.queue_max,
            "extreme_depth": cfg.extreme_depth,
            "max_attempts": cfg.max_attempts,
            "body_max_bytes": cfg.body_max_bytes,
            "bff_drain_interval_sec": cfg.bff_drain_interval_sec,
        }

    @staticmethod
    def _resolve_enabled() -> bool:
        # Hard kill switch for CI / packaging smoke runs.
        if TraceConfigService._env_truthy("NTQ_TRACE_SKIP") is True:
            return False
        env_enabled = TraceConfigService._env_truthy("NTQ_TRACE_ENABLED")
        if env_enabled is not None:
            return env_enabled
        return TraceConsentService.is_granted()

    @staticmethod
    def _env_truthy(name: str) -> Optional[bool]:
        raw = os.environ.get(name)
        if raw is None:
            return None
        return raw.strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _env_str(name: str) -> Optional[str]:
        raw = os.environ.get(name)
        if raw is None or not raw.strip():
            return None
        return raw.strip()

    @staticmethod
    def _env_float(name: str) -> Optional[float]:
        raw = os.environ.get(name)
        if raw is None:
            return None
        try:
            return float(raw)
        except ValueError:
            return None
