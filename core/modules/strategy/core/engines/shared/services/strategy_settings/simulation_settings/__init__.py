"""``settings.simulation`` 子配置包（属 strategy_settings 整块）。

消费者: 见 ``strategy_settings/__init__.py``（不单独拆出）。

::

    execution.py            — BacktestPeriod / ExecutionSettings
    assumption.py           — AssumptionSettings
    assumption_templates.py — AssumptionTemplate
    tradability.py          — TradabilityConfig / Edges / Liquidity / Slippage
    risk_control.py         — RiskControl（settings + 判定 API）
    price.py                — PriceReplaySettings（opportunity_merge_gap）
    simulation_settings.py  — SimulationSettings 门面
"""

from .assumption import AssumptionSettings
from .assumption_templates import AssumptionTemplate
from .execution import BacktestPeriod, ExecutionSettings
from .price import DEFAULT_OPPORTUNITY_MERGE_GAP, PriceReplaySettings
from .risk_control import (
    ForceExitDecision,
    ForceExitRule,
    ForceExitWhenPolicy,
    PendingEnterPolicy,
    RiskControl,
    StatusTagPolicy,
)
from .simulation_settings import SimulationSettings
from .tradability import EdgesConfig, LiquidityConfig, SlippageConfig, TradabilityConfig

__all__ = [
    "AssumptionSettings",
    "AssumptionTemplate",
    "EdgesConfig",
    "BacktestPeriod",
    "ExecutionSettings",
    "ForceExitDecision",
    "ForceExitRule",
    "ForceExitWhenPolicy",
    "PendingEnterPolicy",
    "PriceReplaySettings",
    "LiquidityConfig",
    "DEFAULT_OPPORTUNITY_MERGE_GAP",
    "RiskControl",
    "SimulationSettings",
    "SlippageConfig",
    "StatusTagPolicy",
    "TradabilityConfig",
]
