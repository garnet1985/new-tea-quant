"""MacroLpr Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from ..data_keys import SYS_DATA_KEY
from .loader import MacroLprLoader


MACRO_LPR_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.MACRO_LPR,
        "type": "time_series",
        "scope": "global",
        "display_name": "宏观 LPR",
        "unique_keys": ["date"],
        "loader": MacroLprLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = ['MACRO_LPR_DECLARATION']