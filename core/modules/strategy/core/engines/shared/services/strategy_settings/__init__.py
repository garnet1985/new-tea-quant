"""Strategy settings 整块入口（与 settings.py section 一一对应）。

消费者: scanner, enumerator, price_factor, portfolio
其它: hooks, core.services

建模::

    meta, data, sampling, goal, fees, simulation, portfolio, scanner

不建模（留 raw）::

    is_enabled, core, market_profile
    enumerator / price_simulator（暂缓）

整块 keep：不拆根/叶到各引擎。
"""

from .validation_report import ValidationReport
from .settings_base import SettingsBase
from .meta_settings import MetaSettings
from .data_settings import DataSettings
from .sampling_settings import SamplingSettings
from .goal_settings import ExpirationConfig, GoalSettings, GoalStage, SideLossConfig
from .fees_settings import FeesSettings
from .simulation_settings import (
    AssumptionSettings,
    AssumptionTemplate,
    EdgesConfig,
    ExecutionSettings,
    ForceExitDecision,
    ForceExitRule,
    ForceExitWhenPolicy,
    LiquidityConfig,
    RiskControl,
    SimulationSettings,
    SlippageConfig,
    StatusTagPolicy,
    TradabilityConfig,
)
from .portfolio_settings import AllocationConfig, OutputConfig, PortfolioSettings
from .scanner_settings import ScannerSettings
from .strategy_settings import StrategySettings

__all__ = [
    "ValidationReport",
    "SettingsBase",
    "MetaSettings",
    "DataSettings",
    "SamplingSettings",
    "GoalSettings",
    "GoalStage",
    "SideLossConfig",
    "ExpirationConfig",
    "FeesSettings",
    "AssumptionSettings",
    "AssumptionTemplate",
    "EdgesConfig",
    "ExecutionSettings",
    "ForceExitDecision",
    "ForceExitRule",
    "ForceExitWhenPolicy",
    "LiquidityConfig",
    "RiskControl",
    "SimulationSettings",
    "SlippageConfig",
    "StatusTagPolicy",
    "TradabilityConfig",
    "AllocationConfig",
    "OutputConfig",
    "PortfolioSettings",
    "ScannerSettings",
    "StrategySettings",
]
