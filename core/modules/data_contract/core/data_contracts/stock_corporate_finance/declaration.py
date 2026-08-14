"""Stock Corporate Finance Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from ..data_keys import SYS_DATA_KEY
from .loader import StockCorporateFinanceLoader


# Stock Corporate Finance Declaration
STOCK_CORPORATE_FINANCE_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.STOCK_FINANCE_QUARTERLY,
        "type": "time_series",
        "scope": "per_entity",
        "list_data_key": SYS_DATA_KEY.STOCK_LIST,
        "display_name": "公司财报（季频）",
        "description": "公司财务报表数据（季度序列）",
        "unique_keys": ["id", "quarter"],
        "loader": StockCorporateFinanceLoader,  # 或通过发现机制加载
    },
    # runtime 在声明里不需要，运行时注入：
    # - start_time, end_time（时间范围，但财务数据是季度，可能需要特殊处理）
    # - entity_ids（股票列表）
    # - start_quarter, end_quarter（可选：季度范围，如 "2020Q1", "2020Q4"）
    "specific": {
        # PIT 按披露日推进；勿用默认 "date"（财报行无该字段，until 会始终空）
        "time_axis_field": "ann_date",
    },
}


__all__ = ['STOCK_CORPORATE_FINANCE_DECLARATION']