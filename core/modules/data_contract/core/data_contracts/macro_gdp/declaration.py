"""MacroGdp Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from .loader import MacroGdpLoader


MACRO_GDP_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": "macro.gdp",
        "type": "time_series",
        "scope": "global",
        "display_name": "宏观 GDP",
        "unique_keys": ["quarter"],
        "loader": MacroGdpLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = ['MACRO_GDP_DECLARATION']