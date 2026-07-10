"""Goal settings (``settings.goal``)."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass(frozen=True)
class GoalStage:
    ratio: float
    name: str
    close_invest: bool
    exit_ratio: float  # 0~1；close_invest=True 时为 1.0（全平该 leg）


@dataclass(frozen=True)
class ExpirationConfig:
    window_days: int
    mode: str  # natural_day | trading_day | open_day


@dataclass
class GoalSettings(SettingsBase):
    """``settings.goal`` — stop / take profit / expiration (MVP: first stage each)."""

    raw_settings: Dict[str, Any]

    @property
    def goal(self) -> Dict[str, Any]:
        block = self.raw_settings.get("goal")
        return dict(block) if isinstance(block, dict) else {}

    @property
    def stop_loss(self) -> Optional[GoalStage]:
        return self._parse_block(self.goal.get("stop_loss"), label="goal.stop_loss")

    @property
    def take_profit(self) -> Optional[GoalStage]:
        return self._parse_block(self.goal.get("take_profit"), label="goal.take_profit")

    @property
    def expiration(self) -> Optional[ExpirationConfig]:
        return self._parse_expiration(self.goal.get("expiration"))

    def apply_defaults(self) -> None:
        if "goal" not in self.raw_settings or not isinstance(self.raw_settings["goal"], dict):
            self.raw_settings["goal"] = {}

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        self.apply_defaults()

        raw_goal = self.raw_settings.get("goal")
        if raw_goal is not None and not isinstance(raw_goal, dict):
            SettingsBase.add_critical(
                report,
                "goal",
                "goal must be dict",
                suggested_fix="Set goal to {}",
            )
            return report

        if self.goal.get("stop_loss") is not None:
            try:
                _ = self.stop_loss
            except ValueError as exc:
                SettingsBase.add_critical(report, "goal.stop_loss", str(exc))
        if self.goal.get("take_profit") is not None:
            try:
                _ = self.take_profit
            except ValueError as exc:
                SettingsBase.add_critical(report, "goal.take_profit", str(exc))
        if self.goal.get("expiration") is not None:
            try:
                _ = self.expiration
            except ValueError as exc:
                SettingsBase.add_critical(report, "goal.expiration", str(exc))

        return report

    @staticmethod
    def _to_stage_name(*, label: str, ratio: float) -> str:
        pct = abs(ratio) * 100
        if ratio < 0:
            return f"loss{pct:g}%"
        return f"win{pct:g}%"

    @classmethod
    def _parse_expiration(cls, block: Any) -> Optional[ExpirationConfig]:
        if block is None:
            return None
        if not isinstance(block, dict):
            raise ValueError("goal.expiration 须为 dict")
        try:
            window = int(block.get("fixed_window_in_days") or 0)
        except (TypeError, ValueError):
            return None
        if window <= 0:
            return None
        mode = str(block.get("mode") or "open_day").strip().lower()
        if mode not in {"natural_day", "trading_day", "open_day"}:
            raise ValueError(f"goal.expiration.mode 无效: {mode!r}")
        return ExpirationConfig(window_days=window, mode=mode)

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
        name = raw_name or cls._to_stage_name(label=label, ratio=ratio)

        close_invest = first.get("close_invest") is True
        raw_exit = first.get("exit_ratio", first.get("sell_ratio"))
        if close_invest:
            exit_ratio = 1.0
        elif raw_exit is not None and raw_exit != "":
            exit_ratio = float(raw_exit)
            if exit_ratio <= 0.0 or exit_ratio > 1.0:
                raise ValueError(f"{label}.stages[0].exit_ratio 须在 (0, 1]")
        else:
            raise ValueError(
                f"{label}.stages[0] 须指定 close_invest=True 或 exit_ratio"
                "（settings 仍可读 legacy sell_ratio）"
            )

        return GoalStage(
            ratio=ratio,
            name=name,
            close_invest=close_invest,
            exit_ratio=exit_ratio,
        )

    def exit_price(self, stage: GoalStage, basis_price: float) -> float:
        if basis_price <= 0:
            raise ValueError("basis_price 须 > 0")
        return round(basis_price * (1.0 + stage.ratio), 6)

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return deepcopy(self.goal)


__all__ = ["ExpirationConfig", "GoalSettings", "GoalStage"]
