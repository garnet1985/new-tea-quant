"""价格层跌停顺延卖出重试。

本文件:
- DeferredPendingExit / retry_deferred_exits: 贴板跳过后的后续交易日重试
  边界: 负责 deferred exit 状态机；不负责 JobExecutor 调度或 overall 汇总
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.modules.strategy.core.engines.price_factor.helpers.holding import (
    position_fully_closed,
)
from core.modules.strategy.core.engines.shared.services.safe_values.safe_bar_value import SafeBarValue
from core.modules.strategy.core.engines.shared.services.strategy_settings.simulation_settings.tradability import (
    SlippageConfig,
)


@dataclass
class DeferredPendingExit:
    reason: str
    exit_ratio: float
    triggered_date: str
    deferred_from_date: str = ""


def _leg_date(leg: Dict[str, Any]) -> str:
    return str(leg.get("date") or leg.get("sell_date") or "").strip()


def _leg_exit_ratio(leg: Dict[str, Any]) -> float:
    try:
        return float(leg.get("exit_ratio", leg.get("sell_ratio")) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _ordered_kline_dates(klines: List[Dict[str, Any]]) -> List[str]:
    dates = [
        str(b.get("date") or "").strip()
        for b in klines
        if str(b.get("date") or "").strip()
    ]
    return sorted(set(dates))


def _klines_by_date(klines: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for bar in klines:
        day = str(bar.get("date") or "").strip()
        if day:
            out[day] = bar
    return out


def _exit_fill_model(exit_price_model: str) -> str:
    model = str(exit_price_model or "close").strip().lower() or "close"
    if model == "next_open":
        return "open"
    return model


def _theoretical_exit_price(bar: Dict[str, Any], exit_price_model: str) -> float:
    model = _exit_fill_model(exit_price_model)
    return float(SafeBarValue.price_for_model(bar, model, use_raw=False) or 0.0)


def _is_blocked_at_limit_down(
    price: float,
    bar: Dict[str, Any],
    *,
    entity_id: str,
    market_rules: Any,
    allow_exit_at_limit_down: bool,
) -> bool:
    if allow_exit_at_limit_down:
        return False
    if market_rules is None:
        # 无规则时：若 bar 显式带 sell_at_limit_down 由调用方处理；此处不拦
        return False
    prev = SafeBarValue.optional_float(bar, "pre_close")
    if prev is None or prev <= 0 or not entity_id:
        return False
    try:
        return bool(market_rules.is_at_limit_down(price, prev, entity_id))
    except Exception:
        return False


def _build_executed_leg(
    *,
    source: Dict[str, Any],
    bar: Dict[str, Any],
    sell_price: float,
    buy_price: float,
    at_limit_down: Optional[bool],
) -> Dict[str, Any]:
    exit_ratio = _leg_exit_ratio(source) or 1.0
    basis = float(buy_price or 0.0)
    profit = sell_price - basis
    weighted_profit = profit * exit_ratio
    roi = (weighted_profit / basis) if basis > 0 else 0.0
    day = str(bar.get("date") or "").strip()
    return {
        "date": day,
        "sell_date": day,
        "sell_price": sell_price,
        "exit_ratio": exit_ratio,
        "profit": profit,
        "weighted_profit": weighted_profit,
        "roi": roi,
        "reason": str(source.get("reason") or "").strip(),
        "sell_at_limit_down": at_limit_down,
        "sell_prev_close": SafeBarValue.optional_float(bar, "pre_close") or None,
    }


def retry_deferred_exits(
    *,
    buy_price: float,
    processed_legs: List[Dict[str, Any]],
    skipped_legs: List[Dict[str, Any]],
    klines: List[Dict[str, Any]],
    entity_id: str,
    exit_price_model: str = "close",
    slippage: Optional[SlippageConfig] = None,
    market_rules: Any = None,
    allow_exit_at_limit_down: bool = False,
) -> Tuple[List[Dict[str, Any]], Optional[DeferredPendingExit], int]:
    """对跳过的退出腿按交易日顺延重试。

    返回 ``(processed_legs, pending_or_none, extra_skip_count)``。
    """
    if position_fully_closed(processed_legs) or not skipped_legs:
        return processed_legs, None, 0

    slip = slippage or SlippageConfig()
    by_date = _klines_by_date(klines)
    ordered = _ordered_kline_dates(klines)
    if not ordered:
        return processed_legs, _pending_from_skipped(skipped_legs), 0

    out = list(processed_legs)
    extra_skips = 0
    remaining_skipped = sorted(list(skipped_legs), key=_leg_date)
    start_after = _leg_date(remaining_skipped[0])
    try_dates = [d for d in ordered if d > start_after]

    for day in try_dates:
        if position_fully_closed(out):
            return out, None, extra_skips
        bar = by_date.get(day)
        if not bar:
            continue

        still_pending: List[Dict[str, Any]] = []
        for src in remaining_skipped:
            raw_px = _theoretical_exit_price(bar, exit_price_model)
            if raw_px <= 0:
                still_pending.append(src)
                continue
            sell_px = slip.apply_exit(raw_px)
            blocked = _is_blocked_at_limit_down(
                sell_px,
                bar,
                entity_id=entity_id,
                market_rules=market_rules,
                allow_exit_at_limit_down=allow_exit_at_limit_down,
            )
            if blocked:
                extra_skips += 1
                still_pending.append(src)
                continue
            at_limit: Optional[bool] = None
            prev = SafeBarValue.optional_float(bar, "pre_close")
            if market_rules is not None and prev is not None and prev > 0 and entity_id:
                try:
                    at_limit = bool(
                        market_rules.is_at_limit_down(sell_px, prev, entity_id)
                    )
                except Exception:
                    at_limit = None
            out.append(
                _build_executed_leg(
                    source=src,
                    bar=bar,
                    sell_price=sell_px,
                    buy_price=buy_price,
                    at_limit_down=at_limit,
                )
            )

        remaining_skipped = still_pending
        if not remaining_skipped:
            return out, None, extra_skips

    pending = (
        _pending_from_skipped(remaining_skipped) if remaining_skipped else None
    )
    return out, pending, extra_skips


def _pending_from_skipped(
    skipped: List[Dict[str, Any]],
) -> Optional[DeferredPendingExit]:
    if not skipped:
        return None
    first = skipped[0]
    day = _leg_date(first)
    return DeferredPendingExit(
        reason=str(first.get("reason") or "exit").strip(),
        exit_ratio=_leg_exit_ratio(first) or 1.0,
        triggered_date=day,
        deferred_from_date=day,
    )


__all__ = [
    "DeferredPendingExit",
    "retry_deferred_exits",
]
