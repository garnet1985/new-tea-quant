# TODO: 滚动验证的产品口径还没定，整段先留着，不要当已完成功能。
"""滚动窗口配置。窗口只改模拟起止日，不进执行指纹。"""
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

from ..campaign.config import AttributionConfig


@dataclass
class RollingSettings(SettingsBase):
    """滚动验证配置。窗口是起止日，不是 overlays / matrix 旋钮。"""

    raw_settings: Dict[str, Any]
    _validated: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        self.raw_settings = copy.deepcopy(self.raw_settings)

    @classmethod
    def from_dict(cls, settings: Mapping[str, Any]) -> "RollingSettings":
        """从字典构造滚动配置，尚未校验。"""
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
        """从策略目录读取滚动配置。"""
        parent = AttributionConfig.load(
            strategy_folder, strategy_key=strategy_key
        )
        return cls.to_usable(parent.rolling_payload())

    @classmethod
    def to_usable(
        cls,
        settings: Union[Mapping[str, Any], "RollingSettings", None],
    ) -> "RollingSettings":
        """校验并返回可用的滚动配置。"""
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
        """返回滚动要跑到组合层的上游链。"""
        return (
            SimulateKind.ENUMERATE,
            SimulateKind.PRICE_FACTOR,
            SimulateKind.PORTFOLIO,
        )

    @property
    def simulate_kind(self) -> SimulateKind:
        """滚动固定跑到组合层。"""
        return SimulateKind.PORTFOLIO

    @property
    def windows(self) -> Tuple[Dict[str, str], ...]:
        """返回声明的窗口列表。"""
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
        """补上滚动缺省。"""
        self.raw_settings.pop("fill_missing", None)
        self.raw_settings.pop("steps", None)

    def validate(self) -> ValidationReport:
        """校验窗口并返回报告。"""
        report = SettingsBase.new_validation()
        self.apply_defaults()

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
        """导出滚动配置字典。"""
        self.apply_defaults()
        out = copy.deepcopy(self.raw_settings)
        out["windows"] = [dict(item) for item in self.windows]
        return out
