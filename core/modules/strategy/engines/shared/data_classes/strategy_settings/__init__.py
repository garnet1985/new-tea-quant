#!/usr/bin/env python3
"""Strategy settings dataclasses under engines.shared.

Keep imports lazy to avoid circular-import issues under multiprocessing spawn.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "AllocationConfig",
    "BaseSettings",
    "CapitalAllocationSettings",
    "EnumeratorSettings",
    "ExtremeSameBarOrder",
    "MonitorPriceModel",
    "NoNextBarPolicy",
    "OutputConfig",
    "ScannerSettings",
    "SettingsBase",
    "StrategyCapitalSimulatorSettings",
    "StrategyDataSettings",
    "StrategyEnumeratorSettings",
    "StrategyGoalSettings",
    "StrategyMetaSettings",
    "StrategyPriceFactorSimulationSettings",
    "StrategyPriceSimulatorSettings",
    "StrategySamplingSettings",
    "StrategyScannerSettings",
    "StrategySettings",
    "StrategySimulationSettings",
    "TradePriceModel",
    "ValidationReport",
]


def __getattr__(name: str) -> Any:
    if name in ("SettingsBase", "ValidationReport"):
        from .settings_base import SettingsBase, ValidationReport

        return SettingsBase if name == "SettingsBase" else ValidationReport

    # The remaining dataclasses live in strategy_settings.py（勿用 ``from . import strategy_settings``，
    # 否则在 PEP 562 下会递归触发本包对子模块名 ``strategy_settings`` 的 __getattr__）。
    import importlib

    _m = importlib.import_module(f"{__name__}.strategy_settings")

    if hasattr(_m, name):
        return getattr(_m, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
