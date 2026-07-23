#!/usr/bin/env python3
"""事件模型。"""

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional


@dataclass
class Event:
    event_type: Literal["trigger", "target"]
    date: str
    stock_id: str
    opportunity_id: str
    opportunity: Optional[Dict[str, Any]] = None
    target: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "event_type": self.event_type,
            "date": self.date,
            "stock_id": self.stock_id,
            "opportunity_id": self.opportunity_id,
        }
        if self.opportunity is not None:
            result["opportunity"] = self.opportunity
        if self.target is not None:
            result["target"] = self.target
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            event_type=data.get("event_type", "trigger"),
            date=data.get("date", ""),
            stock_id=data.get("stock_id", ""),
            opportunity_id=data.get("opportunity_id", ""),
            opportunity=data.get("opportunity"),
            target=data.get("target"),
        )

    def is_trigger(self) -> bool:
        return self.event_type == "trigger"

    def is_target(self) -> bool:
        return self.event_type == "target"
