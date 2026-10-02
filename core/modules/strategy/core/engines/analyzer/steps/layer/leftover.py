"""止盈后还有没有涨：本格能不能测，不能编百分比。"""
from __future__ import annotations

from typing import Any, Dict

from core.modules.strategy.core.engines.shared.services.strategy_settings.goal_settings import (
    GoalSettings,
)

_CLOSE = 1.0 - 1e-12


def inspect_leftover(goal_raw: Any) -> Dict[str, Any]:
    """分档未全平、或动态止盈，才能在同一次枚举里看到止盈后路径。"""
    goal = dict(goal_raw) if isinstance(goal_raw, dict) else {}
    if not goal:
        return {"measurable": False, "mode": "unknown"}
    try:
        settings = GoalSettings({"goal": goal})
        stages = settings.take_profit_stages
    except (TypeError, ValueError):
        return {"measurable": False, "mode": "unknown"}
    if not stages:
        return {"measurable": False, "mode": "no_take_profit"}
    first = stages[0]
    first_closes = bool(first.close_invest) or float(first.exit_ratio) >= _CLOSE
    uses_dynamic = any("set_dynamic_loss" in stage.actions for stage in stages)
    if uses_dynamic and not first_closes:
        return {"measurable": True, "mode": "dynamic"}
    if len(stages) >= 2 and not first_closes:
        return {"measurable": True, "mode": "staged"}
    return {"measurable": False, "mode": "single_close"}
