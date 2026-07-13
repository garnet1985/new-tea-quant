"""IndexKlineDaily Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from ..data_keys import SYS_DATA_KEY
from .loader import IndexKlineDailyLoader


INDEX_KLINE_DAILY_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.INDEX_KLINE_DAILY,
        "type": "time_series",
        "scope": "per_entity",
        "display_name": "指数日 K 线",
        "unique_keys": ["id", "term", "date"],
        "loader": IndexKlineDailyLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = ['INDEX_KLINE_DAILY_DECLARATION']