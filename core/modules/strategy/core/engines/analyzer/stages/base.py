"""Attribution stage protocol and shared context."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol


@dataclass
class AttributionContext:
    """Input for one attribution pipeline run (in-memory, post-collect)."""

    source: Dict[str, Any]
    step: str
    decision_space: Dict[str, Any]
    baseline_source: Optional[Dict[str, Any]] = None
    baseline_decision_space: Optional[Dict[str, Any]] = None
    options: Dict[str, Any] = field(default_factory=dict)


class AttributionStage(Protocol):
    name: str

    def run(self, ctx: AttributionContext) -> Dict[str, Any]:
        """Return a fragment to merge under ``report.attribution``."""


__all__ = ["AttributionContext", "AttributionStage"]
