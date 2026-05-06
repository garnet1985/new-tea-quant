#!/usr/bin/env python3
"""Price factor data classes package。

仅急切加载 ``flow_context``，其余符号惰性导出，避免与 ``StrategySettings`` 循环导入。
"""

from __future__ import annotations

from typing import Any

from .flow_context import PriceFactorExecuteContext, PriceFactorPreprocessContext

__all__ = [
    "PriceFactorExecuteContext",
    "PriceFactorPreprocessContext",
    "PriceReport",
    "PriceFactorInvestment",
    "StrategyPriceSimulatorSettings",
    "StrategyPriceFactorSimulationSettings",
]


def __getattr__(name: str) -> Any:
    if name == "PriceReport":
        from .report import PriceReport

        return PriceReport
    if name == "PriceFactorInvestment":
        from .investment import PriceFactorInvestment

        return PriceFactorInvestment
    if name == "StrategyPriceSimulatorSettings":
        from .settings import StrategyPriceSimulatorSettings

        return StrategyPriceSimulatorSettings
    if name == "StrategyPriceFactorSimulationSettings":
        from .settings import StrategyPriceFactorSimulationSettings

        return StrategyPriceFactorSimulationSettings
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
