#!/usr/bin/env python3
"""Enumerator simulator engine.

Package ``__init__`` 不做重依赖 eager import，避免
``strategy_settings → enumerator.data_classes`` 时拉起 flow/worker 与 ``strategy_runtime`` 循环依赖
（多进程 worker 子进程会重新 import，易触发）。
"""

from __future__ import annotations

import importlib
from typing import Any, Tuple

_LAZY_EXPORTS: dict[str, Tuple[str, str]] = {
    "OpportunityEnumeratorFlow": (
        ".opportunity_enumerator_flow",
        "OpportunityEnumeratorFlow",
    ),
    "OpportunityEnumeratorWorker": (".worker", "OpportunityEnumeratorWorker"),
    "OpportunityEnumeratorSettings": (
        ".data_classes",
        "OpportunityEnumeratorSettings",
    ),
    "StrategyEnumeratorSettings": (
        ".data_classes",
        "StrategyEnumeratorSettings",
    ),
    "EnumeratorReport": (".data_classes", "EnumeratorReport"),
    "EnumeratorPreprocessContext": (
        ".data_classes",
        "EnumeratorPreprocessContext",
    ),
    "EnumeratorProbeContext": (".data_classes", "EnumeratorProbeContext"),
    "EnumeratorExecuteContext": (
        ".data_classes",
        "EnumeratorExecuteContext",
    ),
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
