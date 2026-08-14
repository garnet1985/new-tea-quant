"""Trace configuration (defaults + userspace override + env)."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from ...contracts import TraceConfig
from ..defaults import TraceDefaults
from .consent_service import TraceConsentService

logger = logging.getLogger(__name__)

_USERSPACE_TRACE_FILENAME = "trace.json"


class TraceConfigService:
    """Resolve TraceConfig; ``enabled`` comes from user consent (default off)."""

    @staticmethod
    def load() -> TraceConfig:
        base = TraceDefaults.as_dict()
        overlay = TraceConfigService._load_userspace_overrides()
        merged = {**base, **overlay}

        target_url = (
            TraceConfigService._env_str("NTQ_TRACE_ENDPOINT")
            or str(merged.get("target_url") or TraceDefaults.TARGET_URL)
        )
        timeout = TraceConfigService._env_float("NTQ_TRACE_TIMEOUT")
        if timeout is None:
            timeout = float(merged.get("timeout_sec") or TraceDefaults.TIMEOUT_SEC)

        return TraceConfig(
            enabled=TraceConfigService._resolve_enabled(),
            target_url=target_url,
            timeout_sec=timeout,
            queue_max=int(merged.get("queue_max") or TraceDefaults.QUEUE_MAX),
            extreme_depth=int(
                merged.get("extreme_depth") or TraceDefaults.EXTREME_DEPTH
            ),
            max_attempts=int(merged.get("max_attempts") or TraceDefaults.MAX_ATTEMPTS),
            body_max_bytes=int(
                merged.get("body_max_bytes") or TraceDefaults.BODY_MAX_BYTES
            ),
            bff_drain_interval_sec=int(
                merged.get("bff_drain_interval_sec")
                or TraceDefaults.BFF_DRAIN_INTERVAL_SEC
            ),
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
    def userspace_config_path() -> Optional[Path]:
        """``userspace/system/config/trace.json``（tunables；可选）。"""
        try:
            from core.infra.project_context import ProjectContext

            return ProjectContext.path.get_user_config_root() / _USERSPACE_TRACE_FILENAME
        except Exception as exc:
            logger.debug("trace userspace config path unavailable: %s", exc)
            return None

    @staticmethod
    def _load_userspace_overrides() -> Dict[str, Any]:
        path = TraceConfigService.userspace_config_path()
        if path is None or not path.is_file():
            return {}
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
            logger.debug("trace.json read failed: %s", exc)
            return {}
        if not isinstance(raw, dict):
            return {}
        out: Dict[str, Any] = {}
        for key in TraceDefaults.USERSPACE_OVERRIDE_KEYS:
            if key not in raw:
                continue
            value = raw[key]
            if value is None or value == "":
                continue
            out[key] = value
        return out

    @staticmethod
    def _resolve_enabled() -> bool:
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
