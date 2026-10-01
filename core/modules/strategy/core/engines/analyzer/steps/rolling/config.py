"""``attribution.rolling``：滚动窗口外壳（windows；steps 可继承顶层）。

不进 execute_fp / env_fp。窗口只动 ``simulation.execution`` 起止日。
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from core.modules.strategy.core.engines.shared.services.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.validation_report import (
    ValidationReport,
)
from core.modules.strategy.core.enums import SimulateKind

from ..campaign.config import AttributionSettings

_ALLOWED_STEPS = frozenset(k.value for k in SimulateKind)


@dataclass
class RollingSettings(SettingsBase):
    """滚动验证配置。窗口是起止日，不是 matrix 旋钮。"""

    raw_settings: Dict[str, Any]
    _validated: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        self.raw_settings = copy.deepcopy(self.raw_settings)

    @classmethod
    def from_dict(cls, settings: Mapping[str, Any]) -> "RollingSettings":
        if not isinstance(settings, Mapping):
            raise ValueError("rolling 须为 dict")
        return cls(raw_settings=dict(settings))

    @classmethod
    def load(
        cls,
        strategy_folder: Path,
        *,
        strategy_key: Optional[str] = None,
    ) -> "RollingSettings":
        parent = AttributionSettings.load(
            strategy_folder, strategy_key=strategy_key
        )
        return cls.to_usable(parent.rolling_payload())

    @classmethod
    def to_usable(
        cls,
        settings: Union[Mapping[str, Any], "RollingSettings", None],
    ) -> "RollingSettings":
        if isinstance(settings, cls):
            obj = settings
        else:
            obj = cls.from_dict(dict(settings or {}))
        report = obj.validate()
        if not report.is_usable():
            raise ValueError(StrategySettings.format_validation_error(report))
        return obj

    @property
    def steps(self) -> Tuple[SimulateKind, ...]:
        raw = self.raw_settings.get("steps")
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            return ()
        out: list[SimulateKind] = []
        for item in raw:
            text = str(item or "").strip()
            if text not in _ALLOWED_STEPS:
                continue
            out.append(SimulateKind(text))
        return tuple(out)

    @property
    def is_select(self) -> bool:
        return False

    @property
    def simulate_kind(self) -> SimulateKind:
        """steps 最后一步：选号 lookup 用。窗口格按 ``steps`` 逐层 simulate。"""
        steps = self.steps
        if not steps:
            raise ValueError("attribution.steps 不能为空")
        return steps[-1]

    @property
    def windows(self) -> Tuple[Dict[str, str], ...]:
        raw = self.raw_settings.get("windows")
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            return ()
        out: List[Dict[str, str]] = []
        for item in raw:
            if not isinstance(item, Mapping):
                continue
            start = str(item.get("start") or "").strip()
            end = str(item.get("end") or "").strip()
            if start and end:
                out.append({"start": start, "end": end})
        return tuple(out)

    def apply_defaults(self) -> None:
        self.raw_settings.pop("fill_missing", None)

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        self.apply_defaults()

        raw_steps = self.raw_settings.get("steps")
        if raw_steps is None:
            SettingsBase.add_critical(
                report,
                "steps",
                "attribution.steps 必填",
                suggested_fix='Set steps to ["enumerate", "price_factor", "portfolio"]',
            )
        elif not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)) or not raw_steps:
            SettingsBase.add_critical(
                report,
                "steps",
                "attribution.steps 须为非空 list",
                suggested_fix='Set steps to ["enumerate", "price_factor", "portfolio"]',
            )
        else:
            for i, item in enumerate(raw_steps):
                text = str(item or "").strip()
                if text not in _ALLOWED_STEPS:
                    SettingsBase.add_critical(
                        report,
                        f"steps[{i}]",
                        f"未知 step {item!r}",
                        suggested_fix=f"允许 {sorted(_ALLOWED_STEPS)}",
                    )

        raw_windows = self.raw_settings.get("windows")
        if not isinstance(raw_windows, Sequence) or isinstance(raw_windows, (str, bytes)) or not raw_windows:
            SettingsBase.add_critical(
                report,
                "rolling.windows",
                "attribution.rolling.windows 须为非空 list",
                suggested_fix='Set rolling.windows to [{"start": "20230101", "end": "20231231"}]',
            )
            return report

        seen: List[Tuple[str, str]] = []
        for i, item in enumerate(raw_windows):
            if not isinstance(item, Mapping):
                SettingsBase.add_critical(
                    report,
                    f"rolling.windows[{i}]",
                    "须为含 start / end 的 dict",
                )
                continue
            start = str(item.get("start") or "").strip()
            end = str(item.get("end") or "").strip()
            if not start or not end:
                SettingsBase.add_critical(
                    report,
                    f"rolling.windows[{i}]",
                    "start 与 end 必填",
                    suggested_fix="写 YYYYMMDD",
                )
                continue
            if start > end:
                SettingsBase.add_critical(
                    report,
                    f"rolling.windows[{i}]",
                    f"start {start} > end {end}",
                    suggested_fix="Ensure start <= end",
                )
                continue
            pair = (start, end)
            if pair in seen:
                SettingsBase.add_critical(
                    report,
                    f"rolling.windows[{i}]",
                    f"窗口重复 {start}-{end}",
                )
                continue
            seen.append(pair)
        if not seen:
            SettingsBase.add_critical(
                report,
                "rolling.windows",
                "没有可用窗口",
                suggested_fix="至少写一段 start / end",
            )
        return report

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        out = copy.deepcopy(self.raw_settings)
        out["steps"] = [k.value for k in self.steps]
        out["windows"] = [dict(item) for item in self.windows]
        return out
