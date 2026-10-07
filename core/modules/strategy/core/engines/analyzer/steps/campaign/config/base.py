"""战役配置基类：读 attribution.py、校验、标准化。层差异由子类声明。"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Dict, Mapping, Optional, Sequence, Tuple, Union

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

from .allocation import resolve_allocation_axes, validate_allocation
from .inputs import (
    collect_campaign_user_inputs,
    collect_joint_sweep,
    validate_layer_inputs,
)
from .loader import ATTRIBUTION_FILE_NAME, load_attribution_dict

_LAYER_KEYS = ("enumerate", "price_factor", "portfolio")
_REMOVED_KEYS = ("overlays", "matrix")


@dataclass
class AttributionConfigBase(SettingsBase):
    """读取并校验 attribution.py。不展开格子，也不跑模拟。"""

    LAYER: ClassVar[str] = ""
    KIND: ClassVar[SimulateKind] = SimulateKind.PORTFOLIO

    raw_settings: Dict[str, Any]
    _validated: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        self.raw_settings = copy.deepcopy(self.raw_settings)

    @classmethod
    def from_dict(cls, settings: Mapping[str, Any]) -> "AttributionConfigBase":
        """从字典构造配置，尚未校验。"""
        if not isinstance(settings, Mapping):
            raise ValueError("attribution 须为 dict")
        return cls(raw_settings=dict(settings))

    @classmethod
    def load(
        cls,
        strategy_folder: Path,
        *,
        strategy_key: Optional[str] = None,
    ) -> "AttributionConfigBase":
        """从策略目录读取并校验配置。"""
        return cls.to_usable(
            load_attribution_dict(strategy_folder, strategy_key=strategy_key)
        )

    @classmethod
    def to_usable(
        cls,
        settings: Union[Mapping[str, Any], "AttributionConfigBase", None],
    ) -> "AttributionConfigBase":
        """补默认值、校验并返回可用配置。"""
        if isinstance(settings, cls):
            obj = settings
        else:
            obj = cls.from_dict(dict(settings or {}))
        report = obj.validate()
        if not report.is_usable():
            raise ValueError(StrategySettings.format_validation_error(report))
        return obj

    @property
    def layer(self) -> str:
        """返回配置对应的层名。"""
        return self.LAYER

    @property
    def kind(self) -> SimulateKind:
        """返回配置对应的模拟种类。"""
        return self.KIND

    @property
    def campaign_inputs(self) -> Dict[str, Any]:
        """战役共用用户轴（路径键 → values spec）；三 CLI 同一套。"""
        inputs, _cross = collect_campaign_user_inputs(self.raw_settings)
        return inputs

    @property
    def cross(self) -> bool:
        """是否把多个轴做成笛卡尔积。"""
        # TODO: 全轴 cross 能展开，但报告仍按单因素讲，产品还没完成。
        _inputs, cross = collect_campaign_user_inputs(self.raw_settings)
        return cross

    @property
    def joint_sweep(self) -> Tuple[Tuple[str, ...], ...]:
        """可选联合扫描组（路径元组）；全轴 cross 时忽略。"""
        try:
            return tuple(collect_joint_sweep(self.raw_settings))
        except ValueError:
            return ()

    @property
    def has_layer_inputs(self) -> bool:
        """是否写了要展开的参数。"""
        return bool(self.campaign_inputs)

    @property
    def has_parameter(self) -> bool:
        """共用非空 inputs，或顶层 inputs 键存在（空则用共用默认轴）。"""
        if self.has_layer_inputs:
            return True
        if "inputs" in self.raw_settings:
            return True
        allocation = self.raw_settings.get("allocation")
        return isinstance(allocation, Mapping) and bool(allocation)

    @property
    def parameter_mode(self) -> str:
        """返回 cross 或 oaat。"""
        return "cross" if self.cross else "oaat"

    def allocation_axes(
        self, snapshot: Optional[Mapping[str, Any]] = None
    ) -> Dict[str, Tuple[Any, ...]]:
        """资金分配对照轴。未写 ``allocation`` 时按 snapshot 生成默认档。"""
        return resolve_allocation_axes(self.raw_settings, snapshot)

    def rolling_payload(self) -> Dict[str, Any]:
        """返回滚动窗口配置。"""
        block = self.raw_settings.get("rolling")
        nested = dict(block) if isinstance(block, Mapping) else {}
        nested.pop("steps", None)
        nested.pop("fill_missing", None)
        return nested

    def require_parameter(self) -> None:
        """要求当前配置能展开参数。"""
        if any(
            key in self.raw_settings
            and self.raw_settings.get(key) not in (None, [], {})
            for key in _REMOVED_KEYS
        ):
            raise ValueError(
                "attribution.py 已不支持 overlays / matrix；"
                "请写顶层 inputs"
            )
        if not self.has_parameter:
            raise ValueError(
                "attribution.py 没有战役 inputs；"
                "请配置顶层 inputs，再跑 sea / spa / soa"
            )

    def apply_defaults(self) -> None:
        """去掉已废弃字段并补滚动缺省。"""
        self.raw_settings.pop("fill_missing", None)
        self.raw_settings.pop("steps", None)
        rolling = self.raw_settings.get("rolling")
        if isinstance(rolling, dict):
            rolling.pop("fill_missing", None)
            rolling.pop("steps", None)
    def validate(self) -> ValidationReport:
        """校验配置并返回报告。"""
        report = SettingsBase.new_validation()
        self.apply_defaults()
        self._validate_removed_keys(report)
        self._validate_dropped_features(report)
        if "inputs" in self.raw_settings:
            top_block = {
                "inputs": self.raw_settings.get("inputs"),
                "cross": self.raw_settings.get("cross"),
            }
            validate_layer_inputs(
                "campaign",
                top_block,
                report,
                field_prefix="campaign",
            )
        try:
            collect_campaign_user_inputs(self.raw_settings)
        except ValueError as exc:
            SettingsBase.add_critical(
                report,
                "inputs",
                str(exc),
                suggested_fix="轴写在顶层 inputs；cross 只写一处",
            )
        self._validate_joint_sweep(report)
        validate_allocation(self.raw_settings, report)
        # TODO: rolling.windows 仍算一份有效归因配置；口径定了再决定要不要留。
        has_rolling = self._validate_rolling(report)
        has_any_inputs = "inputs" in self.raw_settings
        has_allocation = isinstance(self.raw_settings.get("allocation"), Mapping) and bool(
            self.raw_settings.get("allocation")
        )
        if not has_any_inputs and not has_rolling and not has_allocation:
            SettingsBase.add_critical(
                report,
                "inputs",
                "战役 inputs、rolling.windows 不能都空",
                suggested_fix="写顶层 inputs，或 rolling.windows",
            )
        self._validated = report.is_usable()
        return report

    def _validate_removed_keys(self, report: ValidationReport) -> None:
        for key in _REMOVED_KEYS:
            if key in self.raw_settings and self.raw_settings.get(key) not in (
                None,
                [],
                {},
            ):
                SettingsBase.add_critical(
                    report,
                    key,
                    f"已移除 attribution.{key}；请改用战役 inputs",
                    suggested_fix=(
                        '{"inputs": {"max_pe_percentile": '
                        '{"values": [None, 30]}}, "cross": false}'
                    ),
                )

    def _validate_dropped_features(self, report: ValidationReport) -> None:
        """拒绝已删除的选号、单笔 SHAP 和分层 inputs。"""
        if "versions" in self.raw_settings:
            SettingsBase.add_critical(
                report,
                "versions",
                "已移除 attribution.versions 选号；请改用顶层 inputs",
                suggested_fix='{"inputs": {"max_pe_percentile": {"values": [None, 30]}}}',
            )
        if "shap" in self.raw_settings:
            SettingsBase.add_critical(
                report,
                "shap",
                "已移除单笔 SHAP 附录",
            )
        for key in _LAYER_KEYS:
            if key in self.raw_settings:
                SettingsBase.add_critical(
                    report,
                    key,
                    f"已不支持把轴写在 {key} 块下；请改到顶层 inputs",
                    suggested_fix='{"inputs": {"rsi_oversold_threshold": {"values": [20, 25]}}}',
                )

    def _validate_joint_sweep(self, report: ValidationReport) -> None:
        if "joint_sweep" not in self.raw_settings:
            return
        try:
            groups = collect_joint_sweep(self.raw_settings)
        except ValueError as exc:
            SettingsBase.add_critical(
                report,
                "joint_sweep",
                str(exc),
                suggested_fix='[["stop_loss", "take_profit"]]',
            )
            return
        if not groups:
            return
        if self.cross:
            SettingsBase.add_warning(
                report,
                "joint_sweep",
                "已开启全轴 cross，joint_sweep 将被忽略",
            )
            return
        try:
            inputs, _cross = collect_campaign_user_inputs(self.raw_settings)
        except ValueError:
            return
        for i, group in enumerate(groups):
            for path in group:
                if path not in inputs:
                    SettingsBase.add_critical(
                        report,
                        f"joint_sweep[{i}]",
                        f"轴 {path} 不在 inputs 中",
                        suggested_fix="先在 inputs 声明该轴的 values",
                    )

    # TODO: 滚动验证的产品口径还没定，整段先留着，不要当已完成功能。
    def _validate_rolling(self, report: ValidationReport) -> bool:
        raw = self.raw_settings.get("rolling")
        if raw is None:
            return False
        if not isinstance(raw, Mapping):
            SettingsBase.add_critical(
                report,
                "rolling",
                "attribution.rolling 须为 dict",
                suggested_fix=(
                    'Set rolling to {"windows": '
                    '[{"start": "20230101", "end": "20231231"}]}'
                ),
            )
            return False
        extra = set(raw) - {"windows", "steps"}
        if extra:
            SettingsBase.add_critical(
                report,
                "rolling",
                f"attribution.rolling 不能写 {sorted(extra)}",
                suggested_fix="rolling 只放 windows",
            )
        windows = raw.get("windows")
        if (
            not isinstance(windows, Sequence)
            or isinstance(windows, (str, bytes))
            or not windows
        ):
            SettingsBase.add_critical(
                report,
                "rolling.windows",
                "attribution.rolling.windows 须为非空 list",
                suggested_fix=(
                    'Set rolling.windows to '
                    '[{"start": "20230101", "end": "20231231"}]'
                ),
            )
            return False
        seen: list[tuple[str, str]] = []
        for i, item in enumerate(windows):
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
        return bool(seen)

    def to_dict(self) -> Dict[str, Any]:
        """导出标准化后的配置字典。"""
        self.apply_defaults()
        out = copy.deepcopy(self.raw_settings)
        out.pop("steps", None)
        out.pop("overlays", None)
        out.pop("matrix", None)
        out.pop("versions", None)
        out.pop("shap", None)
        return out
