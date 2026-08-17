"""命中后由框架构建 Opportunity（用户钩子只返回 bool）。

消费者: scanner, enumerator

本文件:
- OpportunityFactory: has_opportunity → Opportunity；无 base bar 则不建
  边界: 负责命中判定与构建；不负责 before/after scan、register、贴板
"""

from __future__ import annotations

from typing import Any, Optional

from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.hooks.hook_params import StrategyContext


class OpportunityFactory:
    """``has_opportunity is True`` 之后建机会。

    边界:
    - 负责: 严格 ``True`` 判定、从当日 base bar 构建 Opportunity
    - 不负责: on_before_scan / on_after_scan、Investment 登记、scan 贴板
    - 调用方: scanner / entity / slice Enumerator 的 Executor
    """

    @staticmethod
    def from_hit(ctx: StrategyContext) -> Optional[Opportunity]:
        """当日无 base bar 返回 None。"""
        rows = ctx.data.items.get(ctx.base_data_key) or []
        if not isinstance(rows, list) or not rows:
            return None
        record = rows[-1]
        if not isinstance(record, dict) or not record:
            return None
        stock_info = dict(ctx.data.entity_info) if ctx.data.entity_info else {}
        return Opportunity(
            stock=stock_info,
            record_of_today=dict(record),
        )

    @classmethod
    def resolve(cls, hook_runtime: Any, ctx: StrategyContext) -> Optional[Opportunity]:
        """调用 ``has_opportunity``；仅 ``True`` 时尝试建 Opportunity。"""
        hit = hook_runtime.call("has_opportunity", ctx)
        if hit is not True:
            return None
        return cls.from_hit(ctx)


__all__ = ["OpportunityFactory"]
