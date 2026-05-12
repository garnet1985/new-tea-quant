#!/usr/bin/env python3
"""Shared engine-level primitives and utilities."""

from importlib import import_module
from typing import Any

__all__ = [
    "ReportBase",
    "SimulatorHooksDispatcher",
    "PerformanceMetrics",
    "PerformanceProfiler",
    "BaseInvestment",
    "Opportunity",
]


def __getattr__(name: str) -> Any:
    if name == "ReportBase":
        return getattr(import_module(".report_base", __name__), name)
    if name in {"SimulatorHooksDispatcher"}:
        return getattr(import_module(".simulator_hooks_dispatcher", __name__), name)
    if name in {"PerformanceMetrics", "PerformanceProfiler"}:
        return getattr(import_module(".performance_profiler", __name__), name)
    if name in {"BaseInvestment", "Opportunity"}:
        return getattr(import_module(".data_classes", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

