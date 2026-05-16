#!/usr/bin/env python3
"""按交易日推进：当日 K 线内完成成交，需「次日 open」的买卖推迟到下一迭代。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    TradePriceModel,
)
from core.modules.strategy.engines.shared.helpers.simulation_pricing import (
    apply_buy_slippage,
    apply_no_next_bar_buy_fallback_price,
    trade_price_defers_to_next_session,
    trade_theoretical_price_on_bar,
)
from core.modules.strategy.enums import OpportunityStatus

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.opportunity import Opportunity
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
        StrategySimulationSettings,
    )


def fill_pending_buys(
    pending: List["Opportunity"],
    active: List["Opportunity"],
    *,
    bar: Dict[str, Any],
    sim: "StrategySimulationSettings",
) -> None:
    """在当日 bar 的 open 上完成昨日信号的 ``next_open`` 买入。"""
    if not pending:
        return
    still_pending: List["Opportunity"] = []
    for opportunity in pending:
        if _fill_buy_on_bar(opportunity, bar=bar, sim=sim):
            opportunity.buy_fill_pending = False
            opportunity.status = OpportunityStatus.ACTIVE.value
            active.append(opportunity)
        else:
            still_pending.append(opportunity)
    pending[:] = still_pending


def execute_pending_exits_on_active(
    active: List["Opportunity"],
    *,
    bar: Dict[str, Any],
    sim: "StrategySimulationSettings",
) -> List[int]:
    """在当日 open 上完成昨日触发的 ``next_open`` 卖出。返回应从 active 移除的下标。"""
    completed: List[int] = []
    for idx, opportunity in enumerate(active):
        if opportunity.execute_pending_exit(sim, bar):
            completed.append(idx)
    return completed


def apply_no_next_bar_buy_fallback(
    opportunity: "Opportunity",
    *,
    signal_bar: Dict[str, Any],
    sim: "StrategySimulationSettings",
) -> bool:
    """样本末尾仍 pending 的买入：按 ``edges.no_next_bar`` 处理。返回是否保留该机会。"""
    policy = sim.edges_no_next_bar
    if policy == "skip_trade":
        return False
    raw = apply_no_next_bar_buy_fallback_price(signal_bar, no_next_bar=policy)
    if raw is None or raw <= 0:
        return policy != "skip_trade"
    opportunity.buy_price = apply_buy_slippage(raw, sim.slippage_buy_bps)
    opportunity.buy_date = str(signal_bar.get("date") or opportunity.trigger_date or "")
    if policy == "unfinished":
        opportunity.status = OpportunityStatus.TESTING.value
    return True


def resolve_pending_buys_at_end(
    pending: List["Opportunity"],
    active: List["Opportunity"],
    all_opportunities: List["Opportunity"],
    *,
    sim: "StrategySimulationSettings",
) -> None:
    """回测最后一根 bar 之后：样本内再无「下一交易日」时的边角处理。"""
    if not pending:
        return
    for opportunity in list(pending):
        signal_bar = opportunity.record_of_today or {}
        keep = apply_no_next_bar_buy_fallback(
            opportunity,
            signal_bar=signal_bar,
            sim=sim,
        )
        pending.remove(opportunity)
        if not keep:
            if opportunity in all_opportunities:
                all_opportunities.remove(opportunity)
            continue
        opportunity.buy_fill_pending = False
        if opportunity.buy_price and opportunity.buy_price > 0:
            opportunity.status = OpportunityStatus.ACTIVE.value
            active.append(opportunity)


def resolve_pending_exits_on_active_at_end(
    active: List["Opportunity"],
    *,
    last_bar: Dict[str, Any],
    sim: "StrategySimulationSettings",
) -> None:
    for opportunity in active:
        if not opportunity.pending_exit:
            continue
        if trade_price_defers_to_next_session(sim.sell_price_model):
            pe = opportunity.pending_exit
            opportunity.pending_exit = None
            opportunity.settle(
                sim,
                last_kline=last_bar,
                reason=pe.get("reason") or "enumeration_end",
            )
        else:
            opportunity.execute_pending_exit(sim, last_bar)


def queue_deferred_buy(opportunity: "Opportunity", *, signal_bar: Dict[str, Any]) -> None:
    opportunity.buy_fill_pending = True
    opportunity.buy_price = 0.0
    opportunity.buy_date = ""
    opportunity.record_of_today = signal_bar
    opportunity.status = OpportunityStatus.TESTING.value


def _fill_buy_on_bar(
    opportunity: "Opportunity",
    *,
    bar: Dict[str, Any],
    sim: "StrategySimulationSettings",
) -> bool:
    raw = trade_theoretical_price_on_bar(
        TradePriceModel.NEXT_OPEN,
        side="buy",
        bar=bar,
    )
    if raw is None or raw <= 0:
        return False
    opportunity.buy_price = apply_buy_slippage(raw, sim.slippage_buy_bps)
    opportunity.buy_date = str(bar.get("date") or "")
    return True


__all__ = [
    "apply_no_next_bar_buy_fallback",
    "execute_pending_exits_on_active",
    "fill_pending_buys",
    "queue_deferred_buy",
    "resolve_pending_buys_at_end",
    "resolve_pending_exits_on_active_at_end",
]
