"""slice_based 单股持仓运行时状态。"""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field
from typing import List, Sequence

from core.modules.strategy.core.engines.shared.data_classes import Opportunity


@dataclass
class EntityHoldings:
    """单股持仓：active 为未平仓，recorded 为全部写入 CSV 的机会。"""

    active: List[Opportunity] = field(default_factory=list)
    recorded: List[Opportunity] = field(default_factory=list)

    def register_entry(self, opportunity: Opportunity) -> None:
        self.active.append(opportunity)
        self.recorded.append(opportunity)

    def force_exit_all(self, as_of: str, close_price: float, *, reason: str) -> None:
        if not self.active:
            return
        for opportunity in self.active:
            opportunity.sell_price = float(close_price)
            opportunity.outcome = "completed"
            opportunity.sell_reason = reason
        self.active.clear()

    def close_expired(
        self,
        as_of: str,
        close_price: float,
        *,
        max_holding_days: int,
        open_dates: Sequence[str],
        reason: str = "max_holding",
    ) -> None:
        if max_holding_days <= 0 or not self.active:
            return
        remaining: List[Opportunity] = []
        for opportunity in self.active:
            trigger = str(opportunity.trigger_date or "").strip()
            if not trigger:
                raise ValueError("active opportunity 缺少 trigger_date")
            held_days = _open_dates_between(trigger, as_of, open_dates)
            if held_days >= max_holding_days:
                opportunity.sell_price = float(close_price)
                opportunity.outcome = "completed"
                opportunity.sell_reason = reason
            else:
                remaining.append(opportunity)
        self.active = remaining


def _open_dates_between(start_date: str, end_date: str, open_dates: Sequence[str]) -> int:
    """含端点的开市日计数。"""
    start = str(start_date).strip()
    end = str(end_date).strip()
    if not start or not end:
        raise ValueError("start_date / end_date 不能为空")
    if start > end:
        raise ValueError(f"无效日期区间: {start} > {end}")
    start_idx = bisect_left(open_dates, start)
    end_idx = bisect_left(open_dates, end)
    if start_idx >= len(open_dates) or open_dates[start_idx] != start:
        raise ValueError(f"{start} 不是有效开市日")
    if end_idx >= len(open_dates) or open_dates[end_idx] != end:
        raise ValueError(f"{end} 不是有效开市日")
    return end_idx - start_idx + 1


__all__ = ["EntityHoldings"]
