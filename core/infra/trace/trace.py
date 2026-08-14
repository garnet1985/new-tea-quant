"""Trace facade — public entry for usage event tracking."""

from __future__ import annotations

from typing import Any, Mapping, Optional, Union

from .contracts import SendBudget, TraceConfig, TraceConsent, TraceEvent
from .core.defaults import TraceDefaults
from .core.namespaces import ConfigNamespace, ConsentNamespace
from .core.services.drain_service import TraceDrainService
from .core.services.permission_service import TracePermissionService
from .core.services.send_service import TraceSendService
from .core.services.track_service import TraceTrackService


class TypesNamespace:
    """与 ``contracts`` / ``defaults`` 同源的类型挂载点。"""

    SendBudget = SendBudget
    TraceConsent = TraceConsent
    TraceConfig = TraceConfig
    TraceEvent = TraceEvent
    TraceDefaults = TraceDefaults


class Trace:
    """
    Usage / behavior tracing facade.

    All APIs are static — call ``Trace.track(...)`` directly; do not instantiate.
    Tracing is opt-in: nothing is collected until the user grants consent.
    Failures never affect callers.
    """

    config = ConfigNamespace()
    consent = ConsentNamespace()
    types = TypesNamespace

    @staticmethod
    def ask_permission(*, source: str = "cli") -> bool:
        """
        Ensure a consent decision exists when possible.

        - Already decided → no-op; return whether granted.
        - Interactive TTY → prompt (``y`` = yes, else no); write decision.
        - Non-TTY → leave undecided; return False (UI / later CLI can ask).

        Returns whether tracing is granted after this call.
        """
        return TracePermissionService.ask(source=source)

    @staticmethod
    def track(event: str, body: Optional[Mapping[str, Any]] = None) -> None:
        """Build one event and POST immediately; on failure enqueue for retry."""
        TraceTrackService.track(event, body)

    @staticmethod
    def queue(event: str, body: Optional[Mapping[str, Any]] = None) -> None:
        """Enqueue one event to the local file queue (no network I/O)."""
        TraceTrackService.queue(event, body)

    @staticmethod
    def send(*, budget: Optional[Union[str, SendBudget]] = None) -> int:
        """
        Drain the local queue under a time/count budget.

        budget: ``standard`` (1s/5), ``extreme`` (2s/10), or ``None``/``auto``.
        """
        return TraceSendService.send(budget=budget)

    @staticmethod
    def start_background_drain() -> None:
        """Start BFF/long-process background drain (idempotent)."""
        TraceDrainService.start()


__all__ = ["Trace"]
