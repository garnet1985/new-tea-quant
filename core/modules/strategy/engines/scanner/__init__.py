#!/usr/bin/env python3
"""Scanner engine package.

Keep imports lazy to avoid circular-import issues under multiprocessing spawn.
"""

from __future__ import annotations

from typing import Any

__all__ = ["Scanner", "ScannerContext", "ScanDateResolver", "ScanCacheManager", "AdapterDispatcher"]


def __getattr__(name: str) -> Any:
    if name == "Scanner":
        from .scanner import Scanner

        return Scanner
    if name == "ScannerContext":
        from .data_classes import ScannerContext

        return ScannerContext
    if name == "ScanDateResolver":
        from .helpers.date_resolver import ScanDateResolver

        return ScanDateResolver
    if name == "ScanCacheManager":
        from .helpers.cache_manager import ScanCacheManager

        return ScanCacheManager
    if name == "AdapterDispatcher":
        from .helpers.adapter_dispatcher import AdapterDispatcher

        return AdapterDispatcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)

