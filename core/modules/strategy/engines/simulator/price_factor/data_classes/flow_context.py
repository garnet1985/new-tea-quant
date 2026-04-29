#!/usr/bin/env python3
"""Typed flow contexts for price factor simulation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
        StrategySettingsView,
    )
    from core.modules.strategy.engines.shared.performance_profiler import AggregateProfiler
    from core.modules.strategy.engines.simulator.price_factor.price_factor_flow_impl import (
        PriceFactorSimulatorConfig,
    )


@dataclass
class PriceFactorPreprocessContext:
    strategy_name: str
    base_settings: "StrategySettingsView"
    simulator_config: "PriceFactorSimulatorConfig"
    output_version_dir: Path
    output_root: Path
    sim_version_dir: Path
    sim_version_id: int
    stock_files: Dict[str, Dict[str, Path]]


@dataclass
class PriceFactorExecuteContext:
    stock_summaries: List[Dict[str, Any]]
    aggregate_profiler: "AggregateProfiler"


__all__ = ["PriceFactorPreprocessContext", "PriceFactorExecuteContext"]
