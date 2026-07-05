"""StockList Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from .loader import StockListLoader


STOCK_LIST_DECLARATION: Dict[str, Any] = {
    "meta": {
        "data_key": "stock.list",
        "type": "non_time_series",
        "scope": "global",
        "display_name": "股票列表",
        "unique_keys": ["id"],
        "loader": StockListLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = ['STOCK_LIST_DECLARATION']