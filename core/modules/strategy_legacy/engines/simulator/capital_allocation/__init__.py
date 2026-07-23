#!/usr/bin/env python3
"""Capital allocation simulator package (side-effect free)."""

from importlib import import_module
from typing import Any

__all__ = [
    "CapitalAllocationFlow",
    "CapitalReport",
    "DateTimeEncoder",
    "AllocationStrategy",
    "FeeCalculator",
]


def __getattr__(name: str) -> Any:
    if name == "CapitalAllocationFlow":
        return getattr(import_module(".capital_allocation_flow", __name__), name)
    if name == "CapitalReport":
        return getattr(import_module(".data_classes.report", __name__), name)
    if name in {"DateTimeEncoder", "AllocationStrategy", "FeeCalculator"}:
        return getattr(import_module(".helpers", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

