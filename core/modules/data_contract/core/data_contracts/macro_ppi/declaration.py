"""MacroPpi Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from .loader import MacroPpiLoader


MACRO_PPI_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": "macro.ppi",
        "type": "time_series",
        "scope": "global",
        "display_name": "宏观 PPI",
        "unique_keys": ["date"],
        "loader": MacroPpiLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = ['MACRO_PPI_DECLARATION']