#!/usr/bin/env python3
"""Shared services across engines."""

from importlib import import_module
from typing import Any

__all__ = [
    "DataLoader",
    "ResultPathManager",
    "VersionManager",
    "StrategyDataManager",
    "StrategyDiscoveryHelper",
    "preload_global_extras_for_enumeration",
    "build_settings",
    "validate_settings",
    "normalize_and_validate",
]


def __getattr__(name: str) -> Any:
    if name in {"DataLoader", "ResultPathManager", "VersionManager"}:
        return getattr(import_module(".artifacts", __name__), name)
    if name == "StrategyDataManager":
        return getattr(import_module(".data", __name__), name)
    if name == "StrategyDiscoveryHelper":
        return getattr(import_module(".discovery", __name__), name)
    if name == "preload_global_extras_for_enumeration":
        return getattr(import_module(".injection", __name__), name)
    if name in {"build_settings", "validate_settings", "normalize_and_validate"}:
        return getattr(import_module(".validation", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
