"""TradeCalendar Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from ..data_keys import SYS_DATA_KEY
from .loader import TradeCalendarLoader


TRADE_CALENDAR_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.TRADE_CALENDAR,
        "type": "time_series",
        "scope": "global",
        "display_name": "交易日历",
        "unique_keys": ["date"],
        "loader": TradeCalendarLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = ['TRADE_CALENDAR_DECLARATION']