"""BE performance baseline — entity_based（null hooks，不产出机会）。

万年基准：只改 BE / 枚举栈，不改本策略业务。

entity_based 不走 calendar asof 市况包；此处仍声明 needs=False 保持与 slice 一致。
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
