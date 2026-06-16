#!/usr/bin/env python3
"""Stock-based（entity_timeline）枚举。"""

from __future__ import annotations

import importlib
from typing import Any, Tuple

_LAZY = {
    "StockBasedEnumeratorFlow": (".flow", "StockBasedEnumeratorFlow"),
    "StockBasedEnumeratorWorker": (".worker", "StockBasedEnumeratorWorker"),
    "run_enumeration_payload": (".worker", "run_enumeration_payload"),
}


def __getattr__(name: str) -> Any:
    spec = _LAZY.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, attr = spec
    module = importlib.import_module(module_path, __name__)
    return getattr(module, attr)


__all__ = list(_LAZY.keys())
