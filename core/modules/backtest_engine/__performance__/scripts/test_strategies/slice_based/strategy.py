"""BE performance baseline — slice_based（null hooks，不产出机会）。

万年基准：只改 BE / SliceOrchestrator，不改本策略业务。

``on_calendar_asof`` 返回空 stocks；``calendar_asof_needs_by_entity`` 为 False，
跳过全宇宙 by_entity 组包（测装载 + PIT + tick，不是扫股）。
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

    def calendar_asof_needs_by_entity(self, ctx: StrategyContext) -> bool:
        _ = ctx
        return False

    def on_calendar_asof(self, ctx: StrategyContext) -> CalendarAsOfResult:
        return CalendarAsOfResult(
            as_of_date=str(ctx.data.now or ""),
            stocks=[],
        )

    def scan_opportunity(self, ctx: StrategyContext) -> Optional[Opportunity]:
        _ = ctx
        return None
