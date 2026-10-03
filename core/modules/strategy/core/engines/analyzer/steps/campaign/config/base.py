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

from .inputs import validate_layer_inputs
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
    def layer_inputs(self) -> Dict[str, Any]:
        raw = self.layer_block.get("inputs")
        return dict(raw) if isinstance(raw, Mapping) else {}

    @property
    def cross(self) -> bool:
        return bool(self.layer_block.get("cross", False))

    @property
    def has_layer_inputs(self) -> bool:
        return bool(self.layer_inputs)

    @property
    def is_select(self) -> bool:
        return bool(self.versions)

    @property
    def has_parameter(self) -> bool:
        """参数归因是否可跑：选号、本层非空 inputs，或本层块存在（空 inputs→默认轴）。"""
        if self.versions:
            return True
        if self.has_layer_inputs:
            return True
        return self.LAYER in self.raw_settings

    @property
    def parameter_mode(self) -> str:
        if self.is_select:
            return "select"
        return "cross" if self.cross else "inputs"

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
                f"attribution.py 没有 {self.LAYER or '本层'}.inputs / versions；"
                "请先配置对照，再跑 sea / spa / soa"
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
        for key in _LAYER_KEYS:
            if key in self.raw_settings:
                validate_layer_inputs(
                    key,
                    self.raw_settings.get(key),
                    report,
                    field_prefix=key,
                )
        has_rolling = self._validate_rolling(report)
        has_any_layer = any(
            isinstance(self.raw_settings.get(key), Mapping)
            for key in _LAYER_KEYS
        )
        if (
            not self.versions
            and not has_any_layer
            and not has_rolling
        ):
            SettingsBase.add_critical(
                report,
                "enumerate",
                "versions、各层 inputs、rolling.windows 不能都空",
                suggested_fix=(
                    '写 enumerate.inputs / price_factor.inputs / '
                    "portfolio.inputs，或 versions / rolling.windows"
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
                    f"已移除 attribution.{key}；请改用按层 inputs",
                    suggested_fix=(
                        'enumerate: {"inputs": {"max_pe_percentile": '
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
        has_inputs = any(
            isinstance(self.raw_settings.get(key), Mapping)
            and bool(
                (self.raw_settings.get(key) or {}).get("inputs")
                if isinstance(self.raw_settings.get(key), Mapping)
                else False
            )
            for key in _LAYER_KEYS
        )
        if has_versions and has_inputs:
            SettingsBase.add_critical(
                report,
                "versions",
                "versions 不要和各层 inputs 同时写；选号是单独一种点名",
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
