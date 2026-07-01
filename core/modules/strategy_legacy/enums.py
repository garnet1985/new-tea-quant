#!/usr/bin/env python3
"""
Strategy 枚举定义
"""

from enum import Enum

# 投资生命周期见 ``engines.shared.data_classes.investment_state``。


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


class Simulator(Enum):
    """模拟器"""

    ENUMERATOR = "enumerator"
    PRICE_FACTOR = "price_factor"
    CAPITAL_ALLOCATION = "capital_allocation"
