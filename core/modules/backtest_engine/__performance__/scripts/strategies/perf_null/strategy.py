"""Null-hook strategy for BE __performance__ enumerate baseline."""
from __future__ import annotations

from typing import Optional

from core.modules.strategy.contracts import (
    CalendarAsOfResult,
    Opportunity,
    StrategyContext,
    StrategyHooks,
)


class PerfNullHooks(StrategyHooks):
    """Exercise data preload + calendar as-of; never emit opportunities.

    Slice path must return the universe from ``on_calendar_asof`` so
    ``scan_opportunity`` still runs (default asof returns stocks=[]).
    """

    def on_calendar_asof(self, ctx: StrategyContext) -> CalendarAsOfResult:
        stocks = [str(sid) for sid in (ctx.data.by_entity or {}) if str(sid).strip()]
        if not stocks:
            stocks = [str(sid) for sid in ctx.data.stock_list if str(sid).strip()]
        return CalendarAsOfResult(
            as_of_date=str(ctx.data.now or ""),
            stocks=stocks,
        )

    def scan_opportunity(self, ctx: StrategyContext) -> Optional[Opportunity]:
        _ = ctx
        return None
