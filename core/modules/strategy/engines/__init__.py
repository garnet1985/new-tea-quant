#!/usr/bin/env python3
"""Strategy engines package (side-effect free)."""

from importlib import import_module
from typing import Any

__all__ = [
    "Scanner",
    "OpportunityEnumeratorFlow",
    "PriceFactorFlow",
    "CapitalAllocationFlow",
    "Analyzer",
    "ReportBase",
    "SimulatorHooksDispatcher",
    "PerformanceMetrics",
    "PerformanceProfiler",
]


def __getattr__(name: str) -> Any:
    if name == "Scanner":
        return getattr(import_module(".scanner", __name__), name)
    if name in {"OpportunityEnumeratorFlow", "PriceFactorFlow", "CapitalAllocationFlow"}:
        return getattr(import_module(".simulator", __name__), name)
    if name == "Analyzer":
        return getattr(import_module(".analyzer", __name__), name)
    if name in {"ReportBase", "SimulatorHooksDispatcher", "PerformanceMetrics", "PerformanceProfiler"}:
        return getattr(import_module(".shared", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

