"""Strategy contracts — public types used across modules."""

from enum import Enum


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


__all__ = ['ExecutionMode', 'SellReason', 'SimulateKind']