"""MacroCpi Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from .loader import MacroCpiLoader


MACRO_CPI_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": "macro.cpi",
        "type": "time_series",
        "scope": "global",
        "display_name": "宏观 CPI",
        "unique_keys": ["date"],
        "loader": MacroCpiLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = ['MACRO_CPI_DECLARATION']