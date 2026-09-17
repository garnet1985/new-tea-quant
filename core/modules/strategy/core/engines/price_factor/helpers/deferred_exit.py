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
from core.modules.strategy.core.engines.shared.services.hfq_roi import hfq_roi
from core.modules.strategy.core.engines.shared.services.safe_values.safe_bar_value import SafeBarValue
from core.modules.strategy.core.engines.shared.services.strategy_settings import (
    StrategySettings,
)


@dataclass
class DeferredPendingExit:
    reason: str
    exit_ratio: float
    triggered_date: str
    deferred_from_date: str = ""


def _goal_date(goal: Dict[str, Any]) -> str:
    return str(goal.get("date") or goal.get("exit_date") or "").strip()


def _goal_exit_ratio(goal: Dict[str, Any]) -> float:
    try:
        return float(goal.get("exit_ratio", goal.get("sell_ratio")) or 0.0)
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


def _theoretical_exit_price(
    bar: Dict[str, Any],
    exit_price_model: str,
    *,
    use_hfq: bool = False,
) -> float:
    model = _exit_fill_model(exit_price_model)
    return float(
        SafeBarValue.price_for_model(bar, model, use_raw=False, use_hfq=use_hfq)
        or 0.0
    )


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
        # 无规则时：若 bar 显式带 exit_at_limit 由调用方处理；此处不拦
        return False
    prev = SafeBarValue.optional_float(bar, "pre_close")
    if prev is None or prev <= 0 or not entity_id:
        return False
    try:
        return bool(market_rules.is_at_limit_down(price, prev, entity_id))
    except Exception:
        return False


def _build_executed_goal(
    *,
    source: Dict[str, Any],
    bar: Dict[str, Any],
    exit_price: float,
    exit_price_hfq: float,
    enter_price_hfq: float,
    at_limit_down: Optional[bool],
) -> Dict[str, Any]:
    exit_ratio = _goal_exit_ratio(source) or 1.0
    roi = hfq_roi(enter_price_hfq, exit_price_hfq)
    basis = float(enter_price_hfq or 0.0)
    profit = roi * basis if basis > 0 else 0.0
    weighted_profit = profit * exit_ratio
    sell_hfq = float(exit_price_hfq or 0.0)
    day = str(bar.get("date") or "").strip()
    return {
        "date": day,
        "exit_date": day,
        "exit_price": exit_price,
        "exit_price_hfq": sell_hfq,
        "exit_ratio": exit_ratio,
        "profit": profit,
        "weighted_profit": weighted_profit,
        "roi": roi,
        "reason": str(source.get("reason") or "").strip(),
        "goal_name": str(source.get("goal_name") or source.get("reason") or "").strip(),
        "price_raw": float(source.get("price_raw") or 0.0),
        "exit_at_limit": at_limit_down,
        "exit_prev_close": SafeBarValue.optional_float(bar, "pre_close") or None,
        "deferred": True,
    }


def retry_deferred_exits(
    *,
    enter_price: float,
    processed_goals: List[Dict[str, Any]],
    skipped_goals: List[Dict[str, Any]],
    klines: List[Dict[str, Any]],
    entity_id: str,
    settings: Optional[StrategySettings] = None,
    market_rules: Any = None,
    enter_price_hfq: float = 0.0,
) -> Tuple[List[Dict[str, Any]], Optional[DeferredPendingExit], int]:
    """对跳过的已触发目标按交易日顺延重试。

    跌停挡板仍看 qfq（bar 顶层 vs ``pre_close``）。新成交价的 ROI 用
    ``enter_price_hfq`` 与 bar ``hfq``；缺合法 hfq 的档 ROI 记 0。
    ``enter_price`` 为 qfq 入场价，仅保留给调用方对称传入。

    返回 ``(processed_goals, pending_or_none, extra_skip_count)``。
    """
    if position_fully_closed(processed_goals) or not skipped_goals:
        return processed_goals, None, 0

    _ = enter_price
    strategy = settings or StrategySettings.from_dict({})
    sim = strategy.simulation
    exit_price_model = str(sim.exit_price or "close")
    slip = sim.tradability.slippage
    allow_exit_at_limit_down = bool(sim.allow_exit_at_limit_down)

    by_date = _klines_by_date(klines)
    ordered = _ordered_kline_dates(klines)
    if not ordered:
        return processed_goals, _pending_from_skipped(skipped_goals), 0

    out = list(processed_goals)
    extra_skips = 0
    remaining_skipped = sorted(list(skipped_goals), key=_goal_date)
    start_after = _goal_date(remaining_skipped[0])
    try_dates = [d for d in ordered if d > start_after]

    for day in try_dates:
        if position_fully_closed(out):
            return out, None, extra_skips
        bar = by_date.get(day)
        if not bar:
            continue

        still_pending: List[Dict[str, Any]] = []
        for src in remaining_skipped:
            qfq_px = _theoretical_exit_price(bar, exit_price_model, use_hfq=False)
            if qfq_px <= 0:
                still_pending.append(src)
                continue
            sell_qfq = slip.apply_exit(qfq_px)
            blocked = _is_blocked_at_limit_down(
                sell_qfq,
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
                        market_rules.is_at_limit_down(sell_qfq, prev, entity_id)
                    )
                except Exception:
                    at_limit = None
            hfq_px = _theoretical_exit_price(bar, exit_price_model, use_hfq=True)
            sell_hfq = slip.apply_exit(hfq_px) if hfq_px > 0 else 0.0
            out.append(
                _build_executed_goal(
                    source=src,
                    bar=bar,
                    exit_price=sell_qfq,
                    exit_price_hfq=sell_hfq,
                    enter_price_hfq=enter_price_hfq,
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
    day = _goal_date(first)
    return DeferredPendingExit(
        reason=str(first.get("reason") or "exit").strip(),
        exit_ratio=_goal_exit_ratio(first) or 1.0,
        triggered_date=day,
        deferred_from_date=day,
    )


__all__ = [
    "DeferredPendingExit",
    "retry_deferred_exits",
]
