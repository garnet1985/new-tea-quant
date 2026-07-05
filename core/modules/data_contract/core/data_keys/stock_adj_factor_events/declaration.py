"""StockAdjFactorEvents Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from .loader import StockAdjFactorEventsLoader


STOCK_ADJ_FACTOR_EVENTS_DECLARATION: Dict[str, Any] = {
    "meta": {
        "data_key": "stock.adj_factor.eventlog",
        "type": "time_series",
        "scope": "per_entity",
        "display_name": "股票复权因子事件",
        "unique_keys": ["id", "event_date"],
        "loader": StockAdjFactorEventsLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = ['STOCK_ADJ_FACTOR_EVENTS_DECLARATION']