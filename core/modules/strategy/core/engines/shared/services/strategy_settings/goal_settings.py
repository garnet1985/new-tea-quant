"""Goal settings (``settings.goal``)."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .settings_base import SettingsBase
from .validation_report import ValidationReport

_ALLOWED_ACTIONS = frozenset({"set_protect_loss", "set_dynamic_loss"})


@dataclass(frozen=True)
class GoalStage:
    ratio: float
    name: str
    close_invest: bool
    exit_ratio: float  # 0~1；close_invest=True 时为 1.0（相对剩余仓位全平）
    actions: Tuple[str, ...] = ()


@dataclass(frozen=True)
class SideLossConfig:
    """``goal.protect_loss`` / ``goal.dynamic_loss``（单块，非 stages）。"""

    ratio: float
    close_invest: bool
    exit_ratio: float
    name: str


@dataclass(frozen=True)
class ExpirationConfig:
    window_days: int
    mode: str  # natural_day | trading_day | open_day


@dataclass
class GoalSettings(SettingsBase):
    """``settings.goal`` — stop / take profit / expiration / protect / dynamic。"""

    raw_settings: Dict[str, Any]

    @property
    def goal(self) -> Dict[str, Any]:
        block = self.raw_settings.get("goal")
        return dict(block) if isinstance(block, dict) else {}

    @property
    def stop_loss_stages(self) -> Tuple[GoalStage, ...]:
        return self._parse_stages(
            self.goal.get("stop_loss"), label="goal.stop_loss"
        )

    @property
    def take_profit_stages(self) -> Tuple[GoalStage, ...]:
        return self._parse_stages(
            self.goal.get("take_profit"),
            label="goal.take_profit",
            require_coverage=True,
        )

    @property
    def stop_loss(self) -> Optional[GoalStage]:
        """首阶段（兼容旧调用）；完整列表见 ``stop_loss_stages``。"""
        stages = self.stop_loss_stages
        return stages[0] if stages else None

    @property
    def take_profit(self) -> Optional[GoalStage]:
        """首阶段（兼容旧调用）；完整列表见 ``take_profit_stages``。"""
        stages = self.take_profit_stages
        return stages[0] if stages else None

    @property
    def protect_loss(self) -> Optional[SideLossConfig]:
        return self._parse_side_loss(
            self.goal.get("protect_loss"),
            label="goal.protect_loss",
            default_name="protect_loss",
        )

    @property
    def dynamic_loss(self) -> Optional[SideLossConfig]:
        return self._parse_side_loss(
            self.goal.get("dynamic_loss"),
            label="goal.dynamic_loss",
            default_name="dynamic_loss",
        )

    @property
    def expiration(self) -> Optional[ExpirationConfig]:
        return self._parse_expiration(self.goal.get("expiration"))

    def apply_defaults(self) -> None:
        if "goal" not in self.raw_settings or not isinstance(
            self.raw_settings["goal"], dict
        ):
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

        for key, prop_name in (
            ("stop_loss", "stop_loss_stages"),
            ("take_profit", "take_profit_stages"),
            ("protect_loss", "protect_loss"),
            ("dynamic_loss", "dynamic_loss"),
            ("expiration", "expiration"),
        ):
            if self.goal.get(key) is None:
                continue
            try:
                getattr(self, prop_name)
            except ValueError as exc:
                SettingsBase.add_critical(report, f"goal.{key}", str(exc))

        return report

    @staticmethod
    def _to_stage_name(*, label: str, ratio: float) -> str:
        pct = abs(ratio) * 100
        if "take_profit" in label or ratio > 0:
            return f"win{pct:g}%"
        if ratio < 0:
            return f"loss{pct:g}%"
        return f"level{pct:g}%"

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
    def _parse_stages(
        cls,
        block: Any,
        *,
        label: str,
        require_coverage: bool = False,
    ) -> Tuple[GoalStage, ...]:
        if block is None:
            return ()
        if not isinstance(block, dict):
            raise ValueError(f"{label} 须为 dict")
        stages_raw = block.get("stages")
        if not isinstance(stages_raw, list) or not stages_raw:
            raise ValueError(f"{label}.stages 须为非空 list")

        out: List[GoalStage] = []
        for idx, item in enumerate(stages_raw):
            out.append(
                cls._parse_stage_item(item, field_path=f"{label}.stages[{idx}]")
            )

        if require_coverage and len(out) > 1:
            cls._validate_take_profit_coverage(out, label=label)
        return tuple(out)

    @classmethod
    def _validate_take_profit_coverage(
        cls, stages: Sequence[GoalStage], *, label: str
    ) -> None:
        if any(stage.close_invest or stage.exit_ratio >= 1.0 - 1e-12 for stage in stages):
            return
        total = sum(float(stage.exit_ratio) for stage in stages)
        if total + 1e-12 < 1.0:
            raise ValueError(
                f"{label}.stages 须至少一阶段 close_invest=True，"
                f"或 exit_ratio 合计 ≥ 1（当前合计={total:g}）"
            )

    @classmethod
    def _parse_stage_item(cls, item: Any, *, field_path: str) -> GoalStage:
        if not isinstance(item, dict):
            raise ValueError(f"{field_path} 须为 dict")
        if "ratio" not in item:
            raise ValueError(f"{field_path} 缺少 ratio")
        ratio = float(item["ratio"])
        raw_name = str(item.get("name") or "").strip()
        # label 用 field_path 前缀推断命名
        label_hint = field_path.rsplit(".stages", 1)[0]
        name = raw_name or cls._to_stage_name(label=label_hint, ratio=ratio)

        close_invest = item.get("close_invest") is True
        raw_exit = item.get("exit_ratio", item.get("sell_ratio"))
        if close_invest:
            exit_ratio = 1.0
        elif raw_exit is not None and raw_exit != "":
            exit_ratio = float(raw_exit)
            if exit_ratio <= 0.0 or exit_ratio > 1.0:
                raise ValueError(f"{field_path}.exit_ratio 须在 (0, 1]")
        else:
            raise ValueError(
                f"{field_path} 须指定 close_invest=True 或 exit_ratio"
                "（settings 仍可读 legacy sell_ratio）"
            )

        actions = cls._parse_actions(
            item.get("actions"), field_path=f"{field_path}.actions"
        )
        return GoalStage(
            ratio=ratio,
            name=name,
            close_invest=close_invest,
            exit_ratio=exit_ratio,
            actions=actions,
        )

    @classmethod
    def _parse_actions(cls, raw: Any, *, field_path: str) -> Tuple[str, ...]:
        if raw is None:
            return ()
        if not isinstance(raw, list):
            raise ValueError(f"{field_path} 须为 list")
        out: List[str] = []
        for idx, item in enumerate(raw):
            action = str(item or "").strip().lower()
            if not action:
                continue
            if action not in _ALLOWED_ACTIONS:
                raise ValueError(
                    f"{field_path}[{idx}] 非法: {item!r}；"
                    f"允许: {sorted(_ALLOWED_ACTIONS)}"
                )
            if action not in out:
                out.append(action)
        return tuple(out)

    @classmethod
    def _parse_side_loss(
        cls,
        block: Any,
        *,
        label: str,
        default_name: str,
    ) -> Optional[SideLossConfig]:
        if block is None:
            return None
        if not isinstance(block, dict):
            raise ValueError(f"{label} 须为 dict")
        if "ratio" not in block:
            raise ValueError(f"{label} 缺少 ratio")
        ratio = float(block["ratio"])
        close_invest = block.get("close_invest") is True
        raw_exit = block.get("exit_ratio", block.get("sell_ratio"))
        if close_invest:
            exit_ratio = 1.0
        elif raw_exit is not None and raw_exit != "":
            exit_ratio = float(raw_exit)
            if exit_ratio <= 0.0 or exit_ratio > 1.0:
                raise ValueError(f"{label}.exit_ratio 须在 (0, 1]")
        else:
            # 默认全平（与 settings_example 一致）
            close_invest = True
            exit_ratio = 1.0
        name = str(block.get("name") or "").strip() or default_name
        return SideLossConfig(
            ratio=ratio,
            close_invest=close_invest,
            exit_ratio=exit_ratio,
            name=name,
        )

    def exit_price(self, stage: GoalStage, basis_price: float) -> float:
        if basis_price <= 0:
            raise ValueError("basis_price 须 > 0")
        return round(basis_price * (1.0 + stage.ratio), 6)

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return deepcopy(self.goal)


__all__ = [
    "ExpirationConfig",
    "GoalSettings",
    "GoalStage",
    "SideLossConfig",
]
