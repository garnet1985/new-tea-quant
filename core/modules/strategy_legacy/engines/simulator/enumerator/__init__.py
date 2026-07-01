#!/usr/bin/env python3
"""Enumerator simulator engine.

Package ``__init__`` 不做重依赖 eager import，避免 settings 解析时拉起 worker 循环依赖。
"""

from __future__ import annotations

import importlib
from typing import Any, Tuple

_LAZY_EXPORTS: dict[str, Tuple[str, str]] = {
    "BaseEnumeratorFlow": (".shared.flow", "BaseEnumeratorFlow"),
    "StockBasedEnumeratorFlow": (".stock_based.flow", "StockBasedEnumeratorFlow"),
    "CalendarSlicedEnumeratorFlow": (".calendar_sliced.flow", "CalendarSlicedEnumeratorFlow"),
    "create_enumerator_flow": (".router", "create_enumerator_flow"),
    "StockBasedEnumeratorWorker": (".stock_based.worker", "StockBasedEnumeratorWorker"),
    "CalendarSlicedEnumeratorWorker": (
        ".calendar_sliced.worker",
        "CalendarSlicedEnumeratorWorker",
    ),
    "EnumeratorSettings": (".shared.settings", "EnumeratorSettings"),
    "StrategyEnumeratorSettings": (".shared.strategy_settings", "StrategyEnumeratorSettings"),
    "EnumeratorReport": (".shared.report", "EnumeratorReport"),
    "EnumeratorPreprocessContext": (".shared.contexts", "EnumeratorPreprocessContext"),
    "EnumeratorProbeContext": (".shared.contexts", "EnumeratorProbeContext"),
    "EnumeratorExecuteContext": (".shared.contexts", "EnumeratorExecuteContext"),
    "CalendarAsOfContext": (".calendar_sliced.types", "CalendarAsOfContext"),
    "CalendarAsOfResult": (".calendar_sliced.types", "CalendarAsOfResult"),
    "PerformanceMetrics": (".helpers", "PerformanceMetrics"),
    "PerformanceProfiler": (".helpers", "PerformanceProfiler"),
    "AggregateProfiler": (".helpers", "AggregateProfiler"),
}


def __getattr__(name: str) -> Any:
    spec = _LAZY_EXPORTS.get(name)
    if spec is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_path, attr = spec
    module = importlib.import_module(module_path, __name__)
    return getattr(module, attr)


__all__ = list(_LAZY_EXPORTS.keys())
