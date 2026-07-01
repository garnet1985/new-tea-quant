"""Calendar as-of data classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CalendarAsOfContext:
    """Calendar as-of context (minimal version)."""

    as_of_date: str
    calendar_name: str = ""
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CalendarAsOfResult:
    """on_calendar_asof 返回值。"""

    as_of_date: str
    stocks: List[str]
    tradable_stocks: Optional[List[str]] = None
    # 跨开市日持久化的策略状态（如 period_selected、force_exit_open_date）
    session_state: Dict[str, Any] = field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None


__all__ = ["CalendarAsOfContext", "CalendarAsOfResult"]
