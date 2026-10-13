"""命中后由框架构建 Opportunity（用户钩子只返回 bool）。

消费者: scanner, enumerator

本文件:
- OpportunityFactory: is_opportunity → Opportunity；无 base bar 则不建
  边界: 负责命中判定与构建；不负责 Investment 登记、scan 贴板
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity
from core.modules.strategy.core.hooks.hook_params import Records, StrategyContext

from .as_of_snapshot import AsOfSnapshot


class OpportunityFactory:
    """``is_opportunity is True`` 之后建机会。

    边界:
    - 负责: 严格 ``True`` 判定、从当日 bar 构建 Opportunity、as-of 快照 + capture 袋
    - 不负责: Investment 登记、scan 贴板
    - 调用方: scanner / entity / slice Enumerator 的 Executor
    """

    @staticmethod
    def from_hit(
        records: Records,
        settings: Any,
        signal_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Optional[Opportunity]:
        """当日无 base bar 返回 None。"""
        record = records.latest
        if not record:
            return None
        stock_info = dict(records.entity_info) if records.entity_info else {}
        snapshot = AsOfSnapshot.merge(
            AsOfSnapshot.build(records, settings),
            signal_snapshot,
        )
        return Opportunity(
            stock=stock_info,
            record_of_today=dict(record),
            signal_snapshot=snapshot,
        )

    @classmethod
    def resolve(
        cls,
        hook_runtime: Any,
        ctx: StrategyContext,
        records: Records,
    ) -> Optional[Opportunity]:
        """调用 ``is_opportunity``；仅 ``True`` 时尝试建 Opportunity。"""
        ctx.clear_captures()
        hit = hook_runtime.call("is_opportunity", ctx, records)
        snapshot = ctx.take_captures()
        if hit is not True:
            return None
        return cls.from_hit(records, ctx.effective_settings, signal_snapshot=snapshot)


__all__ = ["OpportunityFactory"]
