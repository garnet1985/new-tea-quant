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
    """参数归因配置（versions / 按层 inputs / rolling）。

    边界:
    - 负责: 读取、默认值、校验、标准化视图
    - 不负责: 展开格子、simulate、归因计算
    """

    LAYER: ClassVar[str] = ""
    KIND: ClassVar[SimulateKind] = SimulateKind.PORTFOLIO

    raw_settings: Dict[str, Any]
    _validated: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        self.raw_settings = copy.deepcopy(self.raw_settings)

    @classmethod
    def from_dict(cls, settings: Mapping[str, Any]) -> "AttributionConfigBase":
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
        return cls.to_usable(
            load_attribution_dict(strategy_folder, strategy_key=strategy_key)
        )

    @classmethod
    def to_usable(
        cls,
        settings: Union[Mapping[str, Any], "AttributionConfigBase", None],
    ) -> "AttributionConfigBase":
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
        return self.LAYER

    @property
    def kind(self) -> SimulateKind:
        return self.KIND

    @property
    def versions(self) -> Tuple[int, ...]:
        raw = self.raw_settings.get("versions")
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            return ()
        out: list[int] = []
        for item in raw:
            if isinstance(item, bool) or not isinstance(item, (int, str)):
                continue
            try:
                vid = int(item)
            except (TypeError, ValueError):
                continue
            if vid <= 0 or str(vid) != str(item).strip():
                continue
            out.append(vid)
        return tuple(out)

    @property
    def layer_block(self) -> Dict[str, Any]:
        block = self.raw_settings.get(self.LAYER)
        return dict(block) if isinstance(block, Mapping) else {}

    @property
    def campaign_inputs(self) -> Dict[str, Any]:
        """战役共用用户轴（路径键 → values spec）；三 CLI 同一套。"""
        inputs, _cross = collect_campaign_user_inputs(self.raw_settings)
        return inputs

    @property
    def layer_inputs(self) -> Dict[str, Any]:
        """兼容旧名：等于 ``campaign_inputs``（不再是「仅本层块」）。"""
        return self.campaign_inputs

    @property
    def cross(self) -> bool:
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
    def shap_enabled(self) -> bool:
        """价格层单笔 SHAP 附录；默认关，显式 ``shap: true`` 才跑。"""
        if "shap" not in self.raw_settings:
            return False
        return bool(self.raw_settings.get("shap"))

    @property
    def has_layer_inputs(self) -> bool:
        return bool(self.campaign_inputs)

    @property
    def is_select(self) -> bool:
        return bool(self.versions)

    @property
    def has_parameter(self) -> bool:
        """选号、共用非空 inputs，或任一层块 / 顶层 inputs 键存在（空→共用默认轴）。"""
        if self.versions:
            return True
        if self.has_layer_inputs:
            return True
        if "inputs" in self.raw_settings:
            return True
        allocation = self.raw_settings.get("allocation")
        if isinstance(allocation, Mapping) and allocation:
            return True
        return any(key in self.raw_settings for key in _LAYER_KEYS)

    @property
    def parameter_mode(self) -> str:
        if self.is_select:
            return "select"
        return "cross" if self.cross else "inputs"

    def allocation_axes(
        self, snapshot: Optional[Mapping[str, Any]] = None
    ) -> Dict[str, Tuple[Any, ...]]:
        """资金分配对照轴。未写 ``allocation`` 时按 snapshot 生成默认档。"""
        return resolve_allocation_axes(self.raw_settings, snapshot)

    def rolling_payload(self) -> Dict[str, Any]:
        block = self.raw_settings.get("rolling")
        nested = dict(block) if isinstance(block, Mapping) else {}
        nested.pop("steps", None)
        nested.pop("fill_missing", None)
        return nested

    def require_parameter(self) -> None:
        if any(
            key in self.raw_settings
            and self.raw_settings.get(key) not in (None, [], {})
            for key in _REMOVED_KEYS
        ):
            raise ValueError(
                "attribution.py 已不支持 overlays / matrix；"
                "请按层写 inputs，见 ATTRIBUTION_INPUTS.md"
            )
        if not self.has_parameter:
            raise ValueError(
                "attribution.py 没有战役 inputs / versions；"
                "请配置顶层或各层 inputs（共用展格），再跑 sea / spa / soa"
            )

    def apply_defaults(self) -> None:
        self.raw_settings.pop("fill_missing", None)
        self.raw_settings.pop("steps", None)
        rolling = self.raw_settings.get("rolling")
        if isinstance(rolling, dict):
            rolling.pop("fill_missing", None)
            rolling.pop("steps", None)
        if self.raw_settings.get("versions") is None:
            self.raw_settings["versions"] = []
        if self.LAYER and self.LAYER not in self.raw_settings:
            # 不强制写入空块；缺省表示用默认轴
            pass
        self._apply_layer_defaults()

    def _apply_layer_defaults(self) -> None:
        return

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        self.apply_defaults()
        self._validate_removed_keys(report)
        self._validate_versions(report)
        self._validate_mode_exclusivity(report)
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
        for key in _LAYER_KEYS:
            if key in self.raw_settings:
                validate_layer_inputs(
                    key,
                    self.raw_settings.get(key),
                    report,
                    field_prefix=key,
                )
        try:
            collect_campaign_user_inputs(self.raw_settings)
        except ValueError as exc:
            SettingsBase.add_critical(
                report,
                "inputs",
                str(exc),
                suggested_fix="各层 / 顶层同一路径 values 保持一致；cross 只写一处",
            )
        self._validate_joint_sweep(report)
        validate_allocation(self.raw_settings, report)
        has_rolling = self._validate_rolling(report)
        has_any_inputs = (
            "inputs" in self.raw_settings
            or any(
                isinstance(self.raw_settings.get(key), Mapping)
                for key in _LAYER_KEYS
            )
        )
        has_allocation = isinstance(self.raw_settings.get("allocation"), Mapping) and bool(
            self.raw_settings.get("allocation")
        )
        if (
            not self.versions
            and not has_any_inputs
            and not has_rolling
            and not has_allocation
        ):
            SettingsBase.add_critical(
                report,
                "inputs",
                "versions、战役 inputs、rolling.windows 不能都空",
                suggested_fix=(
                    '写顶层 inputs，或 enumerate/price_factor/portfolio.inputs，'
                    "或 versions / rolling.windows"
                ),
            )
        self._validate_layer(report)
        self._validated = report.is_usable()
        return report

    def _validate_layer(self, report: ValidationReport) -> None:
        return

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

    def _validate_versions(self, report: ValidationReport) -> None:
        raw_versions = self.raw_settings.get("versions")
        if raw_versions is None:
            raw_versions = []
        if not isinstance(raw_versions, Sequence) or isinstance(
            raw_versions, (str, bytes)
        ):
            SettingsBase.add_critical(
                report,
                "versions",
                "attribution.versions 须为 list",
                suggested_fix="Set versions to [3, 5] or []",
            )
            return
        for i, item in enumerate(raw_versions):
            if isinstance(item, bool) or not isinstance(item, (int, str)):
                SettingsBase.add_critical(
                    report,
                    f"versions[{i}]",
                    f"须为正整数，收到 {item!r}",
                )
                continue
            try:
                vid = int(item)
            except (TypeError, ValueError):
                SettingsBase.add_critical(
                    report,
                    f"versions[{i}]",
                    f"须为正整数，收到 {item!r}",
                )
                continue
            if vid <= 0 or str(vid) != str(item).strip():
                SettingsBase.add_critical(
                    report,
                    f"versions[{i}]",
                    f"须为正整数，收到 {item!r}",
                )

    def _validate_mode_exclusivity(self, report: ValidationReport) -> None:
        has_versions = bool(self.versions)
        top = self.raw_settings.get("inputs")
        has_top = isinstance(top, Mapping) and bool(top)
        has_layer = any(
            isinstance(self.raw_settings.get(key), Mapping)
            and bool(
                (self.raw_settings.get(key) or {}).get("inputs")
                if isinstance(self.raw_settings.get(key), Mapping)
                else False
            )
            for key in _LAYER_KEYS
        )
        if has_versions and (has_top or has_layer):
            SettingsBase.add_critical(
                report,
                "versions",
                "versions 不要和战役 inputs 同时写；选号是单独一种点名",
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
        self.apply_defaults()
        out = copy.deepcopy(self.raw_settings)
        out.pop("steps", None)
        out.pop("overlays", None)
        out.pop("matrix", None)
        out["versions"] = list(self.versions)
        return out
