"""Stock KLine Daily Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from .loader import StockKlineLoader


# Stock KLine Daily Declaration
STOCK_KLINE_DAILY_DECLARATION: Dict[str, Any] = {
    "meta": {
        "data_key": "stock.kline.daily",
        "type": "time_series",
        "scope": "per_entity",
        "display_name": "股票日K线",
        "description": "股票日K线数据（支持前复权/不复权）",
        "unique_keys": ["date", "stock_id"],
        "loader": StockKlineLoader,  # 或通过发现机制加载
    },
    # runtime 在声明里不需要，运行时注入：
    # - start_time, end_time（时间范围）
    # - entity_ids（股票列表）
    # - adjust（复权方式：qfq/nfq/none）
    # - amount, direction, include_boundary（可选参数）
    "specific": {
        # 没有需要静态声明的特有参数（term 已在 meta.data_key 中体现）
    },
}


__all__ = ['STOCK_KLINE_DAILY_DECLARATION']