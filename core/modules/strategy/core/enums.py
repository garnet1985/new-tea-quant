"""Strategy 模块全局枚举（跨引擎 / Facade 共用）。

本文件:
- ExecutionMode: scan vs simulate
- SellReason: 卖出原因标签
- SimulateKind: simulate 子步骤（enumerate / price_factor / portfolio / full）
  边界: 仅枚举定义；不含 Pipeline 映射或业务逻辑
  常量与默认值见 ``core.const``
"""

from __future__ import annotations

from enum import Enum


class ExecutionMode(Enum):
    """执行模式。"""

    SCAN = "scan"
    SIMULATE = "simulate"


class SellReason(Enum):
    """卖出原因。"""

    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    MAX_HOLDING = "max_holding"
    END_OF_PERIOD = "end_of_period"


class SimulateKind(Enum):
    """模拟类型（Facade simulate 的 step）。"""

    ENUMERATE = "enumerate"
    PRICE_FACTOR = "price_factor"
    PORTFOLIO = "portfolio"
    FULL = "full"


__all__ = ["ExecutionMode", "SellReason", "SimulateKind"]
