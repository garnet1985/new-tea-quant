"""申万行业分类与一级行业列表。"""
from __future__ import annotations

from typing import Any, Dict

from ..data_keys import SYS_DATA_KEY
from .loader import SwIndustryListLoader, SwIndustryLoader


SW_INDUSTRY_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.SW_INDUSTRY,
        "type": "non_time_series",
        "scope": "global",
        "display_name": "申万行业分类",
        "description": "sys_sw_industry，申万 2021 一、二、三级分类树",
        "unique_keys": ["id"],
        "loader": SwIndustryLoader,
    },
    "specific": {},
}

SW_INDUSTRY_LIST_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.SW_INDUSTRY_LIST,
        "type": "non_time_series",
        "scope": "global",
        "display_name": "申万一级行业列表",
        "description": "有日线的实体：一级行业，外加申万 A 指 801003.SI",
        "unique_keys": ["id"],
        "loader": SwIndustryListLoader,
    },
    "specific": {},
}


__all__ = ["SW_INDUSTRY_DECLARATION", "SW_INDUSTRY_LIST_DECLARATION"]
