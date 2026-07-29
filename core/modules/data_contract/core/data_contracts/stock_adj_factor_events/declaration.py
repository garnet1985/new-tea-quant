"""StockAdjFactorEvents Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from ..data_keys import SYS_DATA_KEY
from .loader import StockAdjFactorEventsLoader


STOCK_ADJ_FACTOR_EVENTS_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.STOCK_ADJ_FACTOR_EVENTLOG,
        "type": "time_series",
        "scope": "per_entity",
        "list_data_key": SYS_DATA_KEY.STOCK_LIST,
        "display_name": "股票复权因子事件",
        "unique_keys": ["id", "event_date"],
        "loader": StockAdjFactorEventsLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = ['STOCK_ADJ_FACTOR_EVENTS_DECLARATION']