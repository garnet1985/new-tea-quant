"""跨模块契约：FlushBudget / TraceEvent / TraceConfig / TraceConsent。

推荐::

    from core.infra.trace import Trace
    from core.infra.trace.contracts import FlushBudget
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class FlushBudget(str, Enum):
    """Flush time/count budget names."""

    STANDARD = "standard"
    EXTREME = "extreme"
    AUTO = "auto"


@dataclass(frozen=True)
class TraceConsent:
    """User decision about sharing anonymous debug data (opt-in)."""

    decided: bool = False
    enabled: bool = False
    decided_at: str = ""
    source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decided": self.decided,
            "enabled": self.enabled,
            "decided_at": self.decided_at,
            "source": self.source,
        }


@dataclass(frozen=True)
class TraceConfig:
    """Resolved runtime configuration for tracing."""

    enabled: bool = False
    target_url: str = "https://www.new-tea.cn/api/v1/traces"
    timeout_sec: float = 2.0
    queue_max: int = 100
    extreme_depth: int = 20
    max_attempts: int = 10
    body_max_bytes: int = 4096
    bff_drain_interval_sec: int = 60


@dataclass
class TraceEvent:
    """One queued / transmitted usage event (schema v2)."""

    event_id: str
    installation_id: str
    event: str
    occurred_at: str
    meta: Dict[str, Any] = field(default_factory=dict)
    body: Dict[str, Any] = field(default_factory=dict)
    schema_version: int = 2
    attempts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_wire_dict(self) -> Dict[str, Any]:
        """Payload sent to the remote collector (no local-only fields)."""
        return {
            "schema_version": int(self.schema_version or 2),
            "event_id": str(self.event_id or ""),
            "installation_id": str(self.installation_id or ""),
            "event": str(self.event or ""),
            "occurred_at": str(self.occurred_at or ""),
            "meta": self.meta if isinstance(self.meta, dict) else {},
            "body": self.body if isinstance(self.body, dict) else {},
        }

    @classmethod
    def from_dict(cls, raw: Optional[Dict[str, Any]]) -> Optional["TraceEvent"]:
        if not isinstance(raw, dict):
            return None
        event = raw.get("event") or raw.get("event_name") or ""
        meta = raw.get("meta") if isinstance(raw.get("meta"), dict) else {}
        body = raw.get("body")
        if not isinstance(body, dict):
            body = raw.get("properties") if isinstance(raw.get("properties"), dict) else {}
            if not meta and raw.get("ntq_version"):
                meta = {"ntq_version": str(raw.get("ntq_version"))}
        event_id = str(raw.get("event_id") or "")
        installation_id = str(raw.get("installation_id") or "")
        if not event_id or not installation_id or not event:
            return None
        return cls(
            schema_version=int(raw.get("schema_version") or 2),
            event_id=event_id,
            installation_id=installation_id,
            event=str(event),
            occurred_at=str(raw.get("occurred_at") or ""),
            meta=dict(meta),
            body=dict(body),
            attempts=int(raw.get("attempts") or 0),
        )


__all__ = [
    "FlushBudget",
    "TraceConsent",
    "TraceConfig",
    "TraceEvent",
]
