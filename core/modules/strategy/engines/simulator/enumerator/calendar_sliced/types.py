#!/usr/bin/env python3
"""Calendar slice enumeration user API types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class CalendarAsOfContext:
    as_of_date: str
    slice_id: str
    slice_open_days: int
    window_start: str
    window_end: str
    stocks: Dict[str, Dict[str, Any]]
    carry: Dict[str, Any]
    open_date_index: int
    is_first_open_of_month: bool
    is_last_open_of_month: bool


@dataclass
class CalendarAsOfResult:
    selected_stock_ids: List[str]
    stock_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    carry: Dict[str, Any] = field(default_factory=dict)


__all__ = ["CalendarAsOfContext", "CalendarAsOfResult"]
