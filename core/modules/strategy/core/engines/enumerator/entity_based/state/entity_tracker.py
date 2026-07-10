"""单 entity 枚举 tracker：贯穿时间线跟踪机会与自定义累积数据。"""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from core.modules.strategy.core.engines.shared.data_class import Opportunity
from core.modules.strategy.core.helpers.opportunity_enrichment import OpportunityEnricher


@dataclass
class EntityTracker:
    """单只股票（entity）在完整 calendar 上的枚举状态。

    - ``tracking``：持仓中、尚未完成全部 target 的机会
    - ``recorded``：本 run 内所有机会（含已平仓），供写 CSV
    - ``extras``：策略/用户可在时间线上累积的自定义数据
    """

    entity_id: str
    # 正在tracking当中的
    tracking: List[Opportunity] = field(default_factory=list)
    # 已经结束了的
    completed: List[Opportunity] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)
    _opportunity_index: int = field(default=0, repr=False)

    def process_as_of_date(
        self,
        as_of: str,
        bar: Dict[str, Any],
        *,
        open_dates: Sequence[str],
        max_holding_days: int = 0,
    ) -> None:
        """推进一个交易日：检查 target、过期平仓。"""
        self._close_goal_targets(bar, as_of=as_of)
        if max_holding_days > 0:
            self._close_expired(
                as_of,
                float(bar["close"]),
                max_holding_days=max_holding_days,
                open_dates=open_dates,
            )

    def track_opportunity(
        self,
        opportunity: Opportunity,
        *,
        settings: Dict[str, Any],
        strategy_name: str,
        stock_info: Dict[str, Any],
        trigger_date: str,
        trigger_price: float,
    ) -> None:
        """登记 scan 信号：enrich 后进入 tracking / recorded。"""
        self._opportunity_index += 1
        OpportunityEnricher.apply_trigger_fields(
            opportunity,
            settings=settings,
            strategy_name=strategy_name,
            stock_id=self.entity_id,
            stock_info=stock_info,
            trigger_date=trigger_date,
            trigger_price=trigger_price,
            opportunity_index=self._opportunity_index,
        )
        opportunity.completed_targets = []
        self.tracking.append(opportunity)
        self.completed.append(opportunity)

    def settle_incomplete(
        self,
        as_of: str,
        bar: Dict[str, Any],
        *,
        reason: str = "end_of_simulation",
    ) -> None:
        """模拟结束：对尚未完成全部 target 的 tracking 机会强制平仓。"""
        if not self.tracking:
            return
        close_price = float(bar.get("close") or 0.0)
        for opportunity in list(self.tracking):
            self._close_opportunity(
                opportunity,
                as_of=as_of,
                price=close_price,
                reason=reason,
            )
        self.tracking.clear()

    def recorded_as_dicts(self) -> List[Dict[str, Any]]:
        """供 recorder 写 opportunities / targets CSV。"""
        return [opp.to_dict() for opp in self.completed]

    def _close_goal_targets(self, bar: Dict[str, Any], *, as_of: str) -> None:
        low = float(bar["low"])
        high = float(bar["high"])
        remaining: List[Opportunity] = []
        for opportunity in self.tracking:
            stop = float(opportunity.stop_loss_price or 0)
            target = float(opportunity.target_sell_price or 0)
            if stop > 0 and low <= stop:
                self._close_opportunity(opportunity, as_of=as_of, price=stop, reason="stop_loss")
                continue
            if target > 0 and high >= target:
                self._close_opportunity(opportunity, as_of=as_of, price=target, reason="take_profit")
                continue
            remaining.append(opportunity)
        self.tracking = remaining

    def _close_expired(
        self,
        as_of: str,
        close_price: float,
        *,
        max_holding_days: int,
        open_dates: Sequence[str],
    ) -> None:
        if not self.tracking:
            return
        remaining: List[Opportunity] = []
        for opportunity in self.tracking:
            trigger = str(opportunity.trigger_date or "").strip()
            try:
                held_days = _open_dates_between(trigger, as_of, open_dates)
            except ValueError:
                remaining.append(opportunity)
                continue
            if held_days >= max_holding_days:
                self._close_opportunity(
                    opportunity,
                    as_of=as_of,
                    price=close_price,
                    reason="max_holding",
                )
            else:
                remaining.append(opportunity)
        self.tracking = remaining

    def _close_opportunity(
        self,
        opportunity: Opportunity,
        *,
        as_of: str,
        price: float,
        reason: str,
        sell_ratio: float = 1.0,
    ) -> None:
        basis = float(opportunity.buy_price or opportunity.trigger_price or 0)
        profit = float(price) - basis
        roi = (profit / basis) if basis > 0 else 0.0
        opportunity.completed_targets.append(
            {
                "opportunity_id": opportunity.opportunity_id,
                "date": as_of,
                "price": float(price),
                "sell_price": float(price),
                "sell_ratio": float(sell_ratio),
                "profit": profit,
                "weighted_profit": profit * float(sell_ratio),
                "reason": reason,
                "roi": roi,
            }
        )
        opportunity.sell_price = float(price)
        opportunity.outcome = "completed"
        opportunity.sell_reason = reason


def _open_dates_between(start_date: str, end_date: str, open_dates: Sequence[str]) -> int:
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


__all__ = ["EntityTracker"]
