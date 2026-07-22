"""Strategy settings data classes（与 settings.py section 一一对应）。

建模::

    meta, data, sampling, goal, fees, simulation, portfolio, scanner

不建模（留 raw）::

    is_enabled, core, market_profile
    enumerator / price_simulator（暂缓）
"""

from .validation_report import ValidationReport
from .settings_base import SettingsBase
from .meta_settings import MetaSettings
from .data_settings import DataSettings
from .sampling_settings import SamplingSettings
from .goal_settings import ExpirationConfig, GoalSettings, GoalStage
from .fees_settings import FeesSettings
from .simulation_settings import SimulationSettings
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
    "ExpirationConfig",
    "FeesSettings",
    "SimulationSettings",
    "AllocationConfig",
    "OutputConfig",
    "PortfolioSettings",
    "ScannerSettings",
    "StrategySettings",
]
