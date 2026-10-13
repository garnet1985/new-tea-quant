"""BE performance baseline — entity_based（null hooks，不产出机会）。

万年基准：只改 BE / 枚举栈，不改本策略业务。
"""
from __future__ import annotations

from core.modules.strategy.contracts import Records, StrategyContext, StrategyHooks


class PerfNullHooks(StrategyHooks):
    """Exercise preload + as-of; never scan or emit opportunities."""

    def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool:
        _ = (ctx, records)
        return False
