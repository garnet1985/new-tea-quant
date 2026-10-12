"""申万一级行业日线。"""
from __future__ import annotations

from typing import Any, Dict

from ..data_keys import SYS_DATA_KEY
from .loader import SwIndustryKlineDailyLoader


SW_INDUSTRY_KLINE_DAILY_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.SW_INDUSTRY_KLINE_DAILY,
        "type": "time_series",
        "scope": "per_entity",
        "list_data_key": SYS_DATA_KEY.SW_INDUSTRY_LIST,
        "display_name": "申万一级行业日线",
        "description": "sys_sw_industry_kline。成交量是万股，成交额和市值是万元",
        "unique_keys": ["id", "date"],
        "loader": SwIndustryKlineDailyLoader,
    },
    "specific": {},
}


__all__ = ["SW_INDUSTRY_KLINE_DAILY_DECLARATION"]
