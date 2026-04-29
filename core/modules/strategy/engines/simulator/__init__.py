#!/usr/bin/env python3
"""Simulator engines package (side-effect free)."""

from importlib import import_module
from typing import Any

__all__ = [
    "OpportunityEnumeratorFlow",
    "PriceFactorFlow",
    "CapitalAllocationFlow",
]


def __getattr__(name: str) -> Any:
    if name == "OpportunityEnumeratorFlow":
        return getattr(import_module(".enumerator", __name__), name)
    if name == "PriceFactorFlow":
        return getattr(import_module(".price_factor", __name__), name)
    if name == "CapitalAllocationFlow":
        return getattr(import_module(".capital_allocation", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

