"""IndexList Declaration（meta/runtime/specific 三层结构）。"""
from __future__ import annotations

from typing import Dict, Any

from ..data_keys import SYS_DATA_KEY
from .loader import IndexListLoader


INDEX_LIST_DECLARATION: Dict[str, Any] = {
    "meta": {
        "key": SYS_DATA_KEY.INDEX_LIST,
        "type": "non_time_series",
        "scope": "global",
        "display_name": "指数列表",
        "unique_keys": ["id"],
        "loader": IndexListLoader,
    },
    # runtime 在声明里不需要，运行时注入
    "specific": {},
}


__all__ = ['INDEX_LIST_DECLARATION']