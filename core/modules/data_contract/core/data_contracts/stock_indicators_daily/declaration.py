"""StockIndicatorsDaily Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from .loader import StockIndicatorsDailyLoader


STOCK_INDICATORS_DAILY_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": "stock.indicators.daily",
        "type": "time_series",
        "scope": "per_entity",
        "display_name": "股票日频指标（PE/PB/市值）",
        "unique_keys": ["id", "date"],
        "loader": StockIndicatorsDailyLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = ['STOCK_INDICATORS_DAILY_DECLARATION']