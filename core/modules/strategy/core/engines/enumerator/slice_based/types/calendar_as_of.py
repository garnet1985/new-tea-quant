"""Calendar as-of hook types (slice_based only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class CalendarAsOfContext:
    as_of_date: str = ""


@dataclass
class CalendarAsOfResult:
    as_of_date: str = ""
    stocks: List[str] = field(default_factory=list)
    session_state: Dict[str, Any] = field(default_factory=dict)
    stock_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)


__all__ = ["CalendarAsOfContext", "CalendarAsOfResult"]
