"""IndexWeightDaily Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from .loader import IndexWeightDailyLoader


INDEX_WEIGHT_DAILY_DECLARATION: Dict[str, Any] = {
    "meta": {
        "data_key": "index.weight.daily",
        "type": "time_series",
        "scope": "per_entity",
        "display_name": "指数日频成分权重",
        "unique_keys": ["id", "date", "stock_id"],
        "loader": IndexWeightDailyLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = ['INDEX_WEIGHT_DAILY_DECLARATION']