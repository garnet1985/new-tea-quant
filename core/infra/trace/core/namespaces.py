"""Public namespace classes for Trace facade."""

from __future__ import annotations

from typing import Any, Dict

from .services.config_service import TraceConfigService
from .services.consent_service import TraceConsentService
from .services.permission_service import TracePermissionService


class ConfigNamespace:
    """Trace.config.* — resolved configuration (read-only)."""

    @staticmethod
    def is_enabled() -> bool:
        return TraceConfigService.is_enabled()

    @staticmethod
    def load() -> Dict[str, Any]:
        return TraceConfigService.as_dict()


class ConsentNamespace:
    """Trace.consent.* — user opt-in decision for sharing debug data."""

    @staticmethod
    def is_decided() -> bool:
        """False when the user has never been asked (UI/CLI should prompt)."""
        return TraceConsentService.is_decided()

    @staticmethod
    def needs_ask() -> bool:
        """True when no decision file exists yet."""
        return TracePermissionService.needs_ask()

    @staticmethod
    def is_granted() -> bool:
        return TraceConsentService.is_granted()

    @staticmethod
    def grant(*, source: str = "") -> bool:
        return TraceConsentService.grant(source=source)

    @staticmethod
    def revoke(*, source: str = "") -> bool:
        """Disable tracing and drop any locally queued events."""
        return TraceConsentService.revoke(source=source)

    @staticmethod
    def set(enabled: bool, *, source: str = "") -> bool:
        return TraceConsentService.set(enabled, source=source)

    @staticmethod
    def read() -> Dict[str, Any]:
        return TraceConsentService.read().to_dict()
