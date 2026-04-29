#!/usr/bin/env python3
"""Capital allocation data classes package (side-effect free)."""

from .settings import (
    AllocationConfig,
    CapitalAllocationSettings,
    OutputConfig,
    StrategyCapitalSimulatorSettings,
)

__all__ = [
    "CapitalReport",
    "Account",
    "Position",
    "Event",
    "Trade",
    "CapitalAllocationInvestment",
    "AllocationConfig",
    "OutputConfig",
    "StrategyCapitalSimulatorSettings",
    "CapitalAllocationSettings",
]

