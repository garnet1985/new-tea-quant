"""股票当前申万行业。"""
from __future__ import annotations

from typing import Any, Dict

from ..data_keys import SYS_DATA_KEY
from .loader import StockSwIndustryLoader


STOCK_SW_INDUSTRY_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.STOCK_SW_INDUSTRY,
        "type": "non_time_series",
        "scope": "per_entity",
        "list_data_key": SYS_DATA_KEY.STOCK_LIST,
        "display_name": "股票申万行业",
        "description": "sys_sw_stock_industry_map。一只股票当前的一、二、三级，不是行业变更历史",
        "unique_keys": ["stock_id"],
        "loader": StockSwIndustryLoader,
    },
    "specific": {},
}


__all__ = ["STOCK_SW_INDUSTRY_DECLARATION"]
