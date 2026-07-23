#!/usr/bin/env python3
"""Calendar-sliced 枚举。"""

from __future__ import annotations

import importlib
from typing import Any, Tuple

from .types import CalendarAsOfContext, CalendarAsOfResult

_LAZY = {
    "CalendarSlicedEnumeratorFlow": (".flow", "CalendarSlicedEnumeratorFlow"),
    "CalendarSlicedEnumeratorWorker": (".worker", "CalendarSlicedEnumeratorWorker"),
    "run_calendar_slice_enumeration_payload": (
        ".worker",
        "run_calendar_slice_enumeration_payload",
    ),
}


def __getattr__(name: str) -> Any:
    spec = _LAZY.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, attr = spec
    module = importlib.import_module(module_path, __name__)
    return getattr(module, attr)


__all__ = [
    "CalendarAsOfContext",
    "CalendarAsOfResult",
    *list(_LAZY.keys()),
]
