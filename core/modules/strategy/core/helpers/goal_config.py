"""settings.goal 解析（枚举持仓退出用；settings 已在 StrategySettings 校验）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class GoalStage:
    ratio: float
    name: str
    close_invest: bool


@dataclass(frozen=True)
class GoalConfig:
    stop_loss: Optional[GoalStage]
    take_profit: Optional[GoalStage]

    @classmethod
    def from_settings(cls, settings: Dict[str, Any]) -> GoalConfig:
        if "goal" not in settings:
            return cls(stop_loss=None, take_profit=None)
        goal = settings["goal"]
        if not isinstance(goal, dict):
            raise ValueError("settings.goal 须为 dict")
        return cls(
            stop_loss=cls._parse_block(goal.get("stop_loss"), label="goal.stop_loss"),
            take_profit=cls._parse_block(goal.get("take_profit"), label="goal.take_profit"),
        )

    @staticmethod
    def _infer_stage_name(*, label: str, ratio: float) -> str:
        pct = abs(ratio) * 100
        if ratio < 0:
            return f"loss{pct:g}%"
        return f"win{pct:g}%"

    @classmethod
    def _parse_block(cls, block: Any, *, label: str) -> Optional[GoalStage]:
        if block is None:
            return None
        if not isinstance(block, dict):
            raise ValueError(f"{label} 须为 dict")
        stages = block.get("stages")
        if not isinstance(stages, list) or not stages:
            raise ValueError(f"{label}.stages 须为非空 list")
        first = stages[0]
        if not isinstance(first, dict):
            raise ValueError(f"{label}.stages[0] 须为 dict")
        if "ratio" not in first:
            raise ValueError(f"{label}.stages[0] 缺少 ratio")
        ratio = float(first["ratio"])
        raw_name = str(first.get("name") or "").strip()
        name = raw_name or cls._infer_stage_name(label=label, ratio=ratio)
        close_invest = first.get("close_invest")
        if close_invest is not True:
            raise ValueError(f"{label}.stages[0].close_invest 须为 true")
        return GoalStage(ratio=ratio, name=name, close_invest=True)

    def exit_price(self, stage: GoalStage, trigger_price: float) -> float:
        if trigger_price <= 0:
            raise ValueError("trigger_price 须 > 0")
        return round(trigger_price * (1.0 + stage.ratio), 6)


__all__ = ["GoalConfig", "GoalStage"]
