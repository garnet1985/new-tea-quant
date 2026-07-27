"""价格回测持仓闭合判定（同股互斥门闩）。

本文件:
- position_fully_closed / remaining_position_ratio / resolve_holding_until 等
  边界: 负责 executed_legs 仓位数学；不负责 tradability 或 CSV 写盘
"""

from __future__ import annotations

from typing import Any, Dict, List

_POSITION_EPS = 1e-9
_OPEN_HOLDING_FALLBACK_END = "99991231"


def _leg_exit_ratio(leg: Dict[str, Any]) -> float:
    try:
        return float(leg.get("exit_ratio", leg.get("sell_ratio")) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def remaining_position_ratio(executed_legs: List[Dict[str, Any]]) -> float:
    """``exit_ratio`` 为相对**初始仓位**的绝对份额（与 enum goals CSV 一致，可加总）。

    例：两腿各 0.5 → 剩余 0；若误按「相对剩余」连乘会剩 0.25 并被判未平仓。
    """
    sold = 0.0
    ordered = sorted(
        executed_legs,
        key=lambda t: str(t.get("date") or t.get("exit_date") or ""),
    )
    for leg in ordered:
        ratio = _leg_exit_ratio(leg)
        if ratio <= 0:
            continue
        sold += max(0.0, min(ratio, 1.0))
    return max(0.0, 1.0 - sold)


def position_fully_closed(executed_legs: List[Dict[str, Any]]) -> bool:
    if not executed_legs:
        return False
    return remaining_position_ratio(executed_legs) <= _POSITION_EPS


def latest_executed_exit_date(executed_legs: List[Dict[str, Any]]) -> str:
    dates: List[str] = []
    for leg in executed_legs:
        day = str(leg.get("date") or leg.get("exit_date") or "").strip()
        if day:
            dates.append(day)
    return max(dates) if dates else ""


def resolve_holding_until(
    *,
    processed_legs: List[Dict[str, Any]],
    enter_date: str,
    backtest_end_date: str,
) -> str:
    """平仓后释放至最后成交日；未平仓则锁至回测结束。"""
    if position_fully_closed(processed_legs):
        return latest_executed_exit_date(processed_legs) or str(enter_date or "").strip()
    end = str(backtest_end_date or "").strip()
    return end or _OPEN_HOLDING_FALLBACK_END


__all__ = [
    "latest_executed_exit_date",
    "position_fully_closed",
    "remaining_position_ratio",
    "resolve_holding_until",
]
