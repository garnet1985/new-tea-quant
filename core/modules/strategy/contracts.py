"""Strategy contracts — 跨模块与用户策略的公开 API（类型 + hooks 契约）。"""

from __future__ import annotations

from enum import Enum

from core.modules.strategy.core.engines.enumerator.slice_based.types import (
    CalendarAsOfContext,
    CalendarAsOfResult,
)
from core.modules.strategy.core.engines.shared.data_class import (
    Investment,
    InvestmentRunDeps,
    InvestmentTickInput,
    Opportunity,
)
from core.modules.strategy.core.hooks.base import StrategyHooks
from core.modules.strategy.core.hooks.context import DataContext


class ExecutionMode(Enum):
    """执行模式"""

    SCAN = "scan"
    SIMULATE = "simulate"


class SellReason(Enum):
    """卖出原因"""

    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    MAX_HOLDING = "max_holding"
    END_OF_PERIOD = "end_of_period"


class SimulateKind(Enum):
    """模拟类型"""

    ENUMERATE = "enumerate"
    PRICE_FACTOR = "price_factor"
    CAPITAL_ALLOCATION = "capital_allocation"
    FULL = "full"


__all__ = [
    "CalendarAsOfContext",
    "CalendarAsOfResult",
    "DataContext",
    "ExecutionMode",
    "Opportunity",
    "Investment",
    "InvestmentRunDeps",
    "InvestmentTickInput",
    "SellReason",
    "SimulateKind",
    "StrategyHooks",
]
