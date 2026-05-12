#!/usr/bin/env python3
"""Strategy module public entrypoints.

子包：``engines/``（扫描与模拟）、``execution_manager/``（工作台步骤规划与宿主适配）、
``launcher/``（工作台数据面、枚举 runtime、settings/指纹、扫描异步入口）、``services/``（数据、缓存等）。
"""

from importlib import import_module
from typing import Any

__all__ = [
    "StrategyManager",
    "BaseStrategyWorker",
    "Opportunity",
    "ExecutionMode",
    "OpportunityStatus",
    "SellReason",
    "JobBuilderHelper",
    "ScannerStatisticsHelper",
    "SimulatorStatisticsHelper",
    "StockSamplingHelper",
    "StrategyDataInjectionService",
    "StrategyOutputReaderService",
    "StrategyDiscoveryHelper",
    "build_settings",
    "validate_settings",
    "normalize_and_validate",
]


def __getattr__(name: str) -> Any:
    if name == "StrategyManager":
        return getattr(import_module(".strategy_manager", __name__), name)
    if name == "BaseStrategyWorker":
        return getattr(import_module(".base_strategy_worker", __name__), name)
    if name == "Opportunity":
        return getattr(
            import_module(".engines.shared.data_classes.opportunity", __name__), name
        )
    if name in {"ExecutionMode", "OpportunityStatus", "SellReason"}:
        return getattr(import_module(".enums", __name__), name)
    if name == "ScannerStatisticsHelper":
        return getattr(import_module(".engines.scanner.helpers", __name__), name)
    if name in {"JobBuilderHelper", "StockSamplingHelper"}:
        return getattr(import_module(".engines.shared.helpers", __name__), name)
    if name == "SimulatorStatisticsHelper":
        return getattr(import_module(".engines.simulator.helpers", __name__), name)
    if name in {
        "StrategyDataInjectionService",
        "StrategyOutputReaderService",
        "StrategyDiscoveryHelper",
        "build_settings",
        "normalize_and_validate",
        "validate_settings",
    }:
        return getattr(import_module(".services", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

