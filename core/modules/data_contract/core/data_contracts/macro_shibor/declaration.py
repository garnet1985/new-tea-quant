"""MacroShibor Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Any, Dict

from ..data_keys import SYS_DATA_KEY
from .loader import MacroShiborLoader


MACRO_SHIBOR_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.MACRO_SHIBOR,
        "type": "time_series",
        "scope": "global",
        "display_name": "宏观 Shibor",
        "unique_keys": ["date"],
        "loader": MacroShiborLoader,
    },
    "specific": {},
}


__all__ = ["MACRO_SHIBOR_DECLARATION"]
