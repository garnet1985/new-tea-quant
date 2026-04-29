#!/usr/bin/env python3
"""Shared services across engines."""

from importlib import import_module
from typing import Any

__all__ = [
    "StrategyOutputPathService",
    "StrategyOutputVersionService",
    "StrategyDataInjectionService",
    "StrategyOutputReaderService",
    "StrategyDiscoveryHelper",
    "build_settings",
    "validate_settings",
    "normalize_and_validate",
]


def __getattr__(name: str) -> Any:
    if name in {"StrategyOutputPathService", "StrategyOutputVersionService"}:
        return getattr(import_module(".data", __name__), name)
    if name in {"StrategyDataInjectionService", "StrategyOutputReaderService"}:
        return getattr(import_module(".data", __name__), name)
    if name == "StrategyDiscoveryHelper":
        return getattr(import_module(".discovery", __name__), name)
    if name in {"build_settings", "validate_settings", "normalize_and_validate"}:
        return getattr(import_module(".validation", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
