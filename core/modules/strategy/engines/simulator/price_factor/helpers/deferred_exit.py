#!/usr/bin/env python3
"""价格层：卖出因涨跌停等跳过后，在后续可交易日顺延重试。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.modules.market_profile.profile import MarketProfile
from core.modules.strategy.engines.shared.data_classes.investment_state import PendingExit
from core.modules.strategy.engines.shared.data_classes.strategy_settings.simulation_settings import (
    StrategySimulationSettings,
)
from core.modules.strategy.engines.shared.helpers.tradability import (
    should_skip_sell,
    stamp_target_tradability,
)
from core.modules.strategy.engines.shared.helpers.simulation_pricing import (
    apply_sell_slippage,
    trade_theoretical_price_on_bar,
)
from core.modules.strategy.engines.simulator.price_factor.helpers.holding import (
    position_fully_closed,
    remaining_position_ratio,
)


def _target_date(target: Dict[str, Any]) -> str:
    return str(target.get("date") or target.get("sell_date") or "").strip()


def _target_sell_ratio(target: Dict[str, Any]) -> float:
    try:
        return float(target.get("sell_ratio") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _ordered_kline_dates(klines: List[Dict[str, Any]]) -> List[str]:
    dates = [str(b.get("date") or "").strip() for b in klines if str(b.get("date") or "").strip()]
    return sorted(set(dates))


def _klines_by_date(klines: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for bar in klines:
        day = str(bar.get("date") or "").strip()
        if day:
            out[day] = bar
    return out


def _build_executed_target(
    *,
    source: Dict[str, Any],
    bar: Dict[str, Any],
    prev_bar: Optional[Dict[str, Any]],
    sell_price: float,
    buy_price: float,
    market_profile: MarketProfile,
    stock_id: str,
    stock_status_risk: Any = None,
) -> Dict[str, Any]:
    sell_ratio = _target_sell_ratio(source)
    basis = float(buy_price or 0.0)
    profit = sell_price - basis
    weighted_profit = profit * sell_ratio
    roi = (weighted_profit / basis) if basis > 0 else 0.0
    day = str(bar.get("date") or "").strip()
    row = {
        "opportunity_id": source.get("opportunity_id", ""),
        "date": day,
        "sell_date": day,
        "sell_price": sell_price,
        "sell_ratio": sell_ratio,
        "profit": profit,
        "weighted_profit": weighted_profit,
        "roi": roi,
        "reason": str(source.get("reason") or "").strip(),
    }
    stamp_target_tradability(
        row,
        market_profile,
        stock_id,
        prev_bar,
        sell_price,
        trade_date=day,
        exec_bar=bar,
    )
    return row


def retry_deferred_exits(
    *,
    buy_price: float,
    processed_targets: List[Dict[str, Any]],
    skipped_targets: List[Dict[str, Any]],
    klines: List[Dict[str, Any]],
    sim_settings: StrategySimulationSettings,
    market_profile: MarketProfile,
    stock_id: str,
    allow_sell_at_limit: bool,
) -> Tuple[List[Dict[str, Any]], Optional[PendingExit], int]:
    """
    对跳过的退出目标按交易日顺延重试。

    返回 (更新后的 processed_targets, 仍未成交的 pending_exit, 顺延阶段跳过次数)。
    """
    if position_fully_closed(processed_targets) or not skipped_targets:
        return processed_targets, None, 0

    by_date = _klines_by_date(klines)
    ordered = _ordered_kline_dates(klines)
    if not ordered:
        pe = _pending_from_skipped(skipped_targets)
        return processed_targets, pe, 0

    out = list(processed_targets)
    extra_skips = 0
    remaining_skipped = list(skipped_targets)

    # 仅重试尚未覆盖的跳过目标（按原日期序）
    remaining_skipped.sort(key=_target_date)
    start_after = _target_date(remaining_skipped[0])
    try_dates = [d for d in ordered if d > start_after]

    for day in try_dates:
        if position_fully_closed(out):
            return out, None, extra_skips
        bar = by_date.get(day)
        if not bar:
            continue
        prev_idx = ordered.index(day) - 1
        prev_bar = by_date.get(ordered[prev_idx]) if prev_idx >= 0 else None

        still_pending: List[Dict[str, Any]] = []
        for src in remaining_skipped:
            raw_px = trade_theoretical_price_on_bar(
                sim_settings.sell_price_model,
                side="sell",
                bar=bar,
            )
            if raw_px is None or raw_px <= 0:
                still_pending.append(src)
                continue
            sell_px = apply_sell_slippage(raw_px, sim_settings.slippage_sell_bps)
            probe = {"sell_at_limit_down": None, "sell_prev_close": ""}
            stamp_target_tradability(
                probe,
                market_profile,
                stock_id,
                prev_bar,
                sell_px,
                trade_date=day,
                exec_bar=bar,
            )
            if should_skip_sell(
                {**src, **probe},
                market_profile,
                stock_id,
                sell_px,
                allow_at_limit=allow_sell_at_limit,
            ):
                extra_skips += 1
                still_pending.append(src)
                continue
            executed = _build_executed_target(
                source=src,
                bar=bar,
                prev_bar=prev_bar,
                sell_price=sell_px,
                buy_price=buy_price,
                market_profile=market_profile,
                stock_id=stock_id,
            )
            out.append(executed)

        remaining_skipped = still_pending
        if not remaining_skipped:
            return out, None, extra_skips

    pending = _pending_from_skipped(remaining_skipped) if remaining_skipped else None
    return out, pending, extra_skips


def _pending_from_skipped(skipped: List[Dict[str, Any]]) -> Optional[PendingExit]:
    if not skipped:
        return None
    first = skipped[0]
    return PendingExit(
        reason=str(first.get("reason") or "exit").strip(),
        sell_ratio=_target_sell_ratio(first) or 1.0,
        triggered_date=_target_date(first),
        deferred_from_date=_target_date(first),
    )


def unresolved_exit_remaining_ratio(
    processed_targets: List[Dict[str, Any]],
    skipped_targets: List[Dict[str, Any]],
) -> float:
    """跳过目标若未重试成功，视为仓位仍未按该比例退出。"""
    ratio = remaining_position_ratio(processed_targets)
    if position_fully_closed(processed_targets):
        return ratio
    for src in skipped_targets:
        ratio *= max(0.0, 1.0 - min(_target_sell_ratio(src), 1.0))
    return ratio


__all__ = [
    "retry_deferred_exits",
    "unresolved_exit_remaining_ratio",
]
