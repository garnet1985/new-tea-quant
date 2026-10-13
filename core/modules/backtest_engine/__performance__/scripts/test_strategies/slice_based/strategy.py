"""BE performance baseline — slice_based（null hooks，不产出机会）。

万年基准：只改 BE / SliceOrchestrator，不改本策略业务。

不覆盖 ``on_calendar_slice``，默认返回空列表，不组全宇宙片。
"""
from __future__ import annotations

from core.modules.strategy.contracts import Records, StrategyContext, StrategyHooks


class PerfNullHooks(StrategyHooks):
    """Exercise BE per-slice load + as-of + tick; never scan or emit opportunities."""

    def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool:
        _ = (ctx, records)
        return False
