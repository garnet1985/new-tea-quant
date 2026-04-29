#!/usr/bin/env python3
"""Service-local event DTO for simulator artifact streams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class SimulationEvent:
    event_type: str
    date: str
    stock_id: str
    opportunity_id: str
    opportunity: Optional[Dict[str, Any]] = None
    target: Optional[Dict[str, Any]] = None

    def is_trigger(self) -> bool:
        return self.event_type == "trigger"

    def is_target(self) -> bool:
        return self.event_type == "target"


__all__ = ["SimulationEvent"]
