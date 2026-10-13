"""用户 hook 入参：稳定 ctx，以及当次载荷。"""

from .payloads import CalendarSlice, Opportunities, Records
from .strategy_context import StrategyContext, StrategyInfo, open_context

__all__ = [
    "CalendarSlice",
    "Opportunities",
    "Records",
    "StrategyContext",
    "StrategyInfo",
    "open_context",
]
