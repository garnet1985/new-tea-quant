"""BE performance baseline — entity_based（null hooks，不产出机会）。

万年基准：只改 BE / 枚举栈，不改本策略业务。

``on_calendar_asof`` 返回空 stocks：测装载 + 日历推进，不是每天全宇宙 scan。
"""
from __future__ import annotations

from typing import Optional

from core.modules.strategy.contracts import (
    CalendarAsOfResult,
    Opportunity,
    StrategyContext,
    StrategyHooks,
)


class PerfNullHooks(StrategyHooks):
    """Exercise preload + as-of; never scan or emit opportunities."""

    def on_calendar_asof(self, ctx: StrategyContext) -> CalendarAsOfResult:
        return CalendarAsOfResult(
            as_of_date=str(ctx.data.now or ""),
            stocks=[],
        )

    def scan_opportunity(self, ctx: StrategyContext) -> Optional[Opportunity]:
        _ = ctx
        return None
