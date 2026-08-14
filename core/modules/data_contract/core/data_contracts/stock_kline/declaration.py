"""Stock KLine Declarations（daily/weekly/monthly，meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from ..data_keys import SYS_DATA_KEY
from .loader import StockKlineLoader


# Stock KLine Daily Declaration
STOCK_KLINE_DAILY_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.STOCK_KLINE_DAILY,
        "type": "time_series",
        "scope": "per_entity",
        "list_data_key": SYS_DATA_KEY.STOCK_LIST,
        "display_name": "股票日K线",
        "description": "股票日K线数据（支持前复权/不复权）",
        "unique_keys": ["date", "stock_id"],
        "loader": StockKlineLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}

# Stock KLine Weekly Declaration
STOCK_KLINE_WEEKLY_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.STOCK_KLINE_WEEKLY,
        "type": "time_series",
        "scope": "per_entity",
        "list_data_key": SYS_DATA_KEY.STOCK_LIST,
        "display_name": "股票周K线",
        "description": "股票周K线数据（支持前复权/不复权）",
        "unique_keys": ["date", "stock_id"],
        "loader": StockKlineLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}

# Stock KLine Monthly Declaration
STOCK_KLINE_MONTHLY_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.STOCK_KLINE_MONTHLY,
        "type": "time_series",
        "scope": "per_entity",
        "list_data_key": SYS_DATA_KEY.STOCK_LIST,
        "display_name": "股票月K线",
        "description": "股票月K线数据（支持前复权/不复权）",
        "unique_keys": ["date", "stock_id"],
        "loader": StockKlineLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = [
    'STOCK_KLINE_DAILY_DECLARATION',
    'STOCK_KLINE_WEEKLY_DECLARATION',
    'STOCK_KLINE_MONTHLY_DECLARATION',
]