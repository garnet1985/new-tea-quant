"""Strategy 跨模块公开契约（hooks + 共享数据类型 re-export）。

本文件:
- StrategyHooks / DataContext: 用户策略 hook 契约
- Opportunity / Investment / CalendarAsOf*: 引擎共享数据类
  边界: 仅类型与契约导出；全局枚举见 ``core.enums``；不含编排实现
"""

from __future__ import annotations

from core.modules.strategy.core.engines.shared.data_class import (
    CalendarAsOfContext,
    CalendarAsOfResult,
    Investment,
    InvestmentRunDeps,
    InvestmentTickInput,
    Opportunity,
)
from core.modules.strategy.core.hooks.base import StrategyHooks
from core.modules.strategy.core.hooks.context import DataContext

__all__ = [
    "CalendarAsOfContext",
    "CalendarAsOfResult",
    "DataContext",
    "Opportunity",
    "Investment",
    "InvestmentRunDeps",
    "InvestmentTickInput",
    "StrategyHooks",
]
