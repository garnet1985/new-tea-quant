#!/usr/bin/env python3
"""Shared services across engines."""

from importlib import import_module
from typing import Any

__all__ = [
    "StrategyOutputPathService",
    "StrategyOutputVersionService",
    "StrategyDataInjectionService",
    "StrategyEnumeratorBootstrapService",
    "StrategyOutputReaderService",
    "StrategyDiscoveryHelper",
    "build_settings",
    "validate_settings",
    "normalize_and_validate",
    "EnumeratorRuntimeService",
    "EnumeratorRuntimeContext",
    "StrategyFingerprintManager",
    "StrategyFingerprintRuntimeService",
    "StrategyWorkbenchSnapshotService",
]


def __getattr__(name: str) -> Any:
    if name in {"StrategyOutputPathService", "StrategyOutputVersionService"}:
        return getattr(import_module(".data", __name__), name)
    if name in {
        "StrategyDataInjectionService",
        "StrategyOutputReaderService",
        "StrategyEnumeratorBootstrapService",
    }:
        return getattr(import_module(".data", __name__), name)
    if name == "StrategyDiscoveryHelper":
        return getattr(import_module(".discovery", __name__), name)
    if name in {"build_settings", "validate_settings", "normalize_and_validate"}:
        return getattr(import_module(".validation", __name__), name)
    if name in {"EnumeratorRuntimeService", "EnumeratorRuntimeContext"}:
        return getattr(
            import_module(".cache.simulator_res_db_cache.runtime.enumerator_runtime_service", __name__),
            name,
        )
    if name == "StrategyFingerprintManager":
        return getattr(import_module(".fingerprint", __name__), name)
    if name == "StrategyFingerprintRuntimeService":
        return getattr(import_module(".fingerprint", __name__), name)
    if name == "StrategyWorkbenchSnapshotService":
        return getattr(
            import_module(".cache.simulator_res_db_cache.domain.snapshot_service", __name__),
            name,
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
