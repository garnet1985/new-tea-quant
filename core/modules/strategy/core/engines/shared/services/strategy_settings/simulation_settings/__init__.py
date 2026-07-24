"""``settings.simulation`` 子配置包（属 strategy_settings 整块）。

消费者: 见 ``strategy_settings/__init__.py``（不单独拆出）。

::

    execution.py            — ExecutionSettings
    assumption.py           — AssumptionSettings
    assumption_templates.py — AssumptionTemplate
    tradability.py          — TradabilityConfig / Edges / Liquidity / Slippage
    risk_control.py         — RiskControl（settings + 判定 API）
    simulation_settings.py  — SimulationSettings 门面
"""

from .assumption import AssumptionSettings
from .assumption_templates import AssumptionTemplate
from .execution import ExecutionSettings
from .risk_control import (
    ForceExitDecision,
    ForceExitRule,
    ForceExitWhenPolicy,
    RiskControl,
    StatusTagPolicy,
)
from .simulation_settings import SimulationSettings
from .tradability import EdgesConfig, LiquidityConfig, SlippageConfig, TradabilityConfig

__all__ = [
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
]
