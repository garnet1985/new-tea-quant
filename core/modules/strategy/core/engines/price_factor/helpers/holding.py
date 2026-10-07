"""价格回测持仓闭合判定（单笔仓位数学）。

本文件:
- position_fully_closed / remaining_position_ratio / latest_executed_exit_date
  边界: 负责已成交 completed_goals 仓位数学；不负责 tradability、合并或 CSV 写盘
"""

from __future__ import annotations

from typing import Any, Dict, List

_POSITION_EPS = 1e-9


def _goal_exit_ratio(goal: Dict[str, Any]) -> float:
    try:
        return float(goal.get("exit_ratio") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def remaining_position_ratio(executed_goals: List[Dict[str, Any]]) -> float:
    """``exit_ratio`` 为相对**初始仓位**的绝对份额（与 enum goals CSV 一致，可加总）。

    例：两档各 0.5 → 剩余 0；若误按「相对剩余」连乘会剩 0.25 并被判未平仓。
    """
    sold = 0.0
    ordered = sorted(
        executed_goals,
        key=lambda t: str(t.get("date") or t.get("exit_date") or ""),
    )
    for goal in ordered:
        ratio = _goal_exit_ratio(goal)
        if ratio <= 0:
            continue
        sold += max(0.0, min(ratio, 1.0))
    return max(0.0, 1.0 - sold)


def position_fully_closed(executed_goals: List[Dict[str, Any]]) -> bool:
    if not executed_goals:
        return False
    return remaining_position_ratio(executed_goals) <= _POSITION_EPS


def latest_executed_exit_date(executed_goals: List[Dict[str, Any]]) -> str:
    dates: List[str] = []
    for goal in executed_goals:
        day = str(goal.get("date") or goal.get("exit_date") or "").strip()
        if day:
            dates.append(day)
    return max(dates) if dates else ""


__all__ = [
    "latest_executed_exit_date",
    "position_fully_closed",
    "remaining_position_ratio",
]
