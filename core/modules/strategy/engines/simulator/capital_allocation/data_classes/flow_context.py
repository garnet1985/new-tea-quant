#!/usr/bin/env python3
"""Typed flow contexts for capital allocation simulation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
        StrategySettingsView,
    )
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
        StrategySimulationSettings,
    )
    from core.modules.strategy.engines.shared.performance_profiler import PerformanceProfiler
    from core.modules.strategy.engines.simulator.capital_allocation.data_classes.settings import (
        StrategyCapitalSimulatorSettings,
    )
    from core.modules.strategy.services.data.output import SimulationEvent


@dataclass
class CapitalAllocationPreprocessContext:
    strategy_name: str
    base_settings: "StrategySettingsView"
    simulation_settings: "StrategySimulationSettings"
    config: "StrategyCapitalSimulatorSettings"
    output_version_dir: Path
    sim_version_dir: Path
    sim_version_id: int
    profiler: "PerformanceProfiler"


@dataclass
class CapitalAllocationExecuteContext:
    empty: bool = False
    events: Optional[List["SimulationEvent"]] = None
    account: Optional[Any] = None
    trades: Optional[List[Dict[str, Any]]] = None
    equity_curve: Optional[List[Dict[str, Any]]] = None
    completed_opportunities_map: Optional[Dict[str, Dict[str, Any]]] = None


__all__ = ["CapitalAllocationPreprocessContext", "CapitalAllocationExecuteContext"]
