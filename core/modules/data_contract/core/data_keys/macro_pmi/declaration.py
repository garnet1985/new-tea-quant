"""MacroPmi Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from .loader import MacroPmiLoader


MACRO_PMI_DECLARATION: Dict[str, Any] = {
    "meta": {
        "data_key": "macro.pmi",
        "type": "time_series",
        "scope": "global",
        "display_name": "PMI（采购经理指数）",
        "unique_keys": ["date"],
        "loader": MacroPmiLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = ['MACRO_PMI_DECLARATION']