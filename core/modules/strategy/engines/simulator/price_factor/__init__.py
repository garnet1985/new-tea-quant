#!/usr/bin/env python3
"""Price factor simulator package (side-effect free)."""

from importlib import import_module
from typing import Any

__all__ = [
    "PriceFactorFlow",
    "PriceFactorWorker",
    "PriceReport",
    "DateTimeEncoder",
    "parse_yyyymmdd",
    "to_ratio",
    "to_percent",
    "get_annual_return",
]


def __getattr__(name: str) -> Any:
    if name == "PriceFactorFlow":
        return getattr(import_module(".price_factor_flow", __name__), name)
    if name == "PriceFactorWorker":
        return getattr(import_module(".worker", __name__), name)
    if name == "PriceReport":
        return getattr(import_module(".data_classes.report", __name__), name)
    if name in {
        "DateTimeEncoder",
        "parse_yyyymmdd",
        "to_ratio",
        "to_percent",
        "get_annual_return",
    }:
        return getattr(import_module(".helpers", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

