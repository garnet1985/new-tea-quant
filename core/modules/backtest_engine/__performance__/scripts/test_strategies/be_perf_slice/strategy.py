"""BE performance baseline — slice_based（null hooks，不产出机会）。

万年基准：只改 BE / SliceOrchestrator，不改本策略业务。

``on_calendar_asof`` 必须返回 ``stocks=[]``：测的是装载 + as-of 切窗 + tick，
不是每天全宇宙 scan。若返回全股票列表，会把墙钟打成「策略扫股」而非 BE。
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
    """Exercise BE per-slice load + as-of + tick; never scan or emit opportunities."""

    def on_calendar_asof(self, ctx: StrategyContext) -> CalendarAsOfResult:
        return CalendarAsOfResult(
            as_of_date=str(ctx.data.now or ""),
            stocks=[],
        )

    def scan_opportunity(self, ctx: StrategyContext) -> Optional[Opportunity]:
        _ = ctx
        return None
