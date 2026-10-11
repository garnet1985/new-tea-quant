"""货币供应量。"""
from __future__ import annotations

from typing import Any, Dict

from ..data_keys import SYS_DATA_KEY
from .loader import MacroMoneySupplyLoader


MACRO_MONEY_SUPPLY_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.MACRO_MONEY_SUPPLY,
        "type": "time_series",
        "scope": "global",
        "display_name": "货币供应量",
        "unique_keys": ["date"],
        "loader": MacroMoneySupplyLoader,
    },
    "specific": {},
}


__all__ = ["MACRO_MONEY_SUPPLY_DECLARATION"]
