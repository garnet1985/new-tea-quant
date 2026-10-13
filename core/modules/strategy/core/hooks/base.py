"""用户 StrategyHooks。

稳定的 ctx 在每个钩子里一样。当日要操作的对象是显式入参。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Sequence, Union

from core.modules.strategy.core.engines.shared.data_class import Opportunity
from core.modules.strategy.core.hooks.hook_params import (
    CalendarSlice,
    Opportunities,
    Records,
    StrategyContext,
)


class StrategyHooks(ABC):
    """用户策略 hooks 基类。"""

    def to_sample_list(
        self, ctx: StrategyContext, stock_list: Sequence[str]
    ) -> Sequence[str]:
        """回测开始前调用一次，在指纹之前。

        ``stock_list`` 已是数据库宇宙经 ``settings.sampling`` 过滤后的列表。
        默认原样返回。覆盖时做确定性的语义过滤。
        返回值会与入参取交、排序，写入 ``ctx.sample_list`` 和指纹。
        """
        _ = ctx
        return list(stock_list or [])

    def on_calendar_slice(
        self, ctx: StrategyContext, calendar_slice: CalendarSlice
    ) -> List[str]:
        """``slice_based`` 每个日历日：返回进入 ``is_opportunity`` 的 id。"""
        _ = (ctx, calendar_slice)
        return []

    @abstractmethod
    def is_opportunity(self, ctx: StrategyContext, records: Records) -> bool:
        """当日该股票是否有机会。只返回 True / False。

        命中后框架用当日 bar 建 Opportunity。归因用 ``ctx.capture``。
        跨日变量放 ``ctx.state``。
        """

    def is_new_opportunity(
        self,
        ctx: StrategyContext,
        *,
        previous: Any,
        gap: Any,
    ) -> bool:
        """价格回放：本笔是否开新段。仅 price_factor 调用。

        ``True`` 开新段。没有上一笔时必须 ``True``。
        ``previous`` 是上一笔结果或 None。``gap`` 是 base 轴步数，算不出则为 None。
        默认按 ``simulation.price.opportunity_merge_gap``。
        """
        if previous is None or gap is None:
            return True
        try:
            steps = int(gap)
        except (TypeError, ValueError):
            return True
        limit = ctx.effective_settings.simulation.price.opportunity_merge_gap
        return steps > int(limit)

    def select_portfolio_entries(
        self, ctx: StrategyContext, opportunities: Opportunities
    ) -> Sequence[Union[Opportunity, str]]:
        """挑选当日进入组合的机会。

        返回 Opportunity 或 opportunity id。不返回仓位。
        未覆盖时，组合层用配置排序填剩余槽位，不会调用本默认实现。
        ``opportunities.account`` 含 ``held_entity_ids`` 与 ``remaining_slots``。
        """
        _ = (ctx, opportunities)
        return []

    def is_stop_loss(
        self,
        ctx: StrategyContext,
        records: Records,
        *,
        custom: str,
        stage: Any,
    ) -> bool:
        """自定义止损。仅当某 stop_loss 段声明了 ``custom`` 时调用。"""
        _ = (ctx, records, stage)
        raise NotImplementedError(
            f"unsupported stop_loss custom={str(custom or '').strip()!r}"
        )

    def is_take_profit(
        self,
        ctx: StrategyContext,
        records: Records,
        *,
        custom: str,
        stage: Any,
    ) -> bool:
        """自定义止盈。仅当某 take_profit 段声明了 ``custom`` 时调用。"""
        _ = (ctx, records, stage)
        raise NotImplementedError(
            f"unsupported take_profit custom={str(custom or '').strip()!r}"
        )


__all__ = ["StrategyHooks"]
