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

from .grid import SettingsMatrix
from .loader import ATTRIBUTION_FILE_NAME, load_attribution_dict
from .overlay import SettingsOverlay


@dataclass
class AttributionConfigBase(SettingsBase):
    """参数归因配置（versions / overlays / matrix；rolling 块原样保留给滚动管线）。

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

    # --- 标准化视图 ---------------------------------------------------------

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
    def overlays(self) -> Tuple[SettingsOverlay, ...]:
        raw = self.raw_settings.get("overlays")
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            return ()
        return tuple(
            SettingsOverlay.from_dict(row)
            for row in raw
            if isinstance(row, Mapping)
        )

    @property
    def has_overlays(self) -> bool:
        return bool(self.overlays)

    @property
    def has_matrix(self) -> bool:
        raw = self.raw_settings.get("matrix")
        return isinstance(raw, Mapping) and bool(raw)

    @property
    def is_select(self) -> bool:
        return bool(self.versions)

    @property
    def has_parameter(self) -> bool:
        """参数归因是否有可对照的声明（不含 rolling）。"""
        return bool(self.versions) or self.has_overlays or self.has_matrix

    @property
    def parameter_modes(self) -> Tuple[str, ...]:
        if self.is_select:
            return ("select",)
        out: list[str] = []
        if self.has_overlays:
            out.append("overlays")
        if self.has_matrix:
            out.append("matrix")
        return tuple(out)

    @property
    def parameter_mode(self) -> str:
        modes = self.parameter_modes
        if not modes:
            return "overlays"
        return "+".join(modes)

    def rolling_payload(self) -> Dict[str, Any]:
        """交给滚动管线的 ``rolling`` 块。"""
        block = self.raw_settings.get("rolling")
        nested = dict(block) if isinstance(block, Mapping) else {}
        nested.pop("steps", None)
        nested.pop("fill_missing", None)
        return nested

    def require_parameter(self) -> None:
        """参数归因入口：没有 overlays/matrix/versions 则拒绝。"""
        if not self.has_parameter:
            raise ValueError(
                "attribution.py 没有 overlays / matrix / versions；"
                "请先配置对照，再跑 sea / spa / soa"
            )

    # --- SettingsBase -------------------------------------------------------

    def apply_defaults(self) -> None:
        self.raw_settings.pop("fill_missing", None)
        self.raw_settings.pop("steps", None)
        rolling = self.raw_settings.get("rolling")
        if isinstance(rolling, dict):
            rolling.pop("fill_missing", None)
            rolling.pop("steps", None)
        if self.raw_settings.get("versions") is None:
            self.raw_settings["versions"] = []
        self._apply_layer_defaults()

    def _apply_layer_defaults(self) -> None:
        """子类可覆盖：本层额外默认值。"""
        return

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        self.apply_defaults()
        self._validate_versions(report)
        self._validate_overlays(report)
        SettingsMatrix.validate(self.raw_settings.get("matrix"), report)
        self._validate_mode_exclusivity(report)
        has_rolling = self._validate_rolling(report)
        if not self.has_parameter and not has_rolling:
            SettingsBase.add_critical(
                report,
                "overlays",
                "versions、overlays、matrix、rolling.windows 不能都空",
                suggested_fix=(
                    "写 overlays 做逐项对照，matrix 做参数交叉对照（可同时写），"
                    "versions 选号，或 rolling.windows 做滚动"
                ),
            )
        self._validate_layer(report)
        self._validated = report.is_usable()
        return report

    def _validate_layer(self, report: ValidationReport) -> None:
        """子类可覆盖：本层额外约束。"""
        return

    def _validate_versions(self, report: ValidationReport) -> None:
        raw_versions = self.raw_settings.get("versions")
        if raw_versions is None:
            raw_versions = []
        if not isinstance(raw_versions, Sequence) or isinstance(raw_versions, (str, bytes)):
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

    def _validate_overlays(self, report: ValidationReport) -> None:
        raw_overlays = self.raw_settings.get("overlays")
        if raw_overlays is None:
            raw_overlays = []
        if not isinstance(raw_overlays, Sequence) or isinstance(raw_overlays, (str, bytes)):
            SettingsBase.add_critical(
                report,
                "overlays",
                "attribution.overlays 须为 list",
                suggested_fix="Set overlays to a list of overlay dicts or []",
            )
            return
        for i, row in enumerate(raw_overlays):
            if not isinstance(row, Mapping) or not row:
                SettingsBase.add_critical(
                    report,
                    f"overlays[{i}]",
                    "须为非空 dict overlay",
                )
                continue
            overlay_report = SettingsOverlay.from_dict(row).validate()
            for err in overlay_report.errors:
                err = dict(err)
                err["field_path"] = (
                    f"overlays[{i}].{err.get('field_path') or ''}"
                ).rstrip(".")
                report.errors.append(err)
                report.is_valid = False

    def _validate_mode_exclusivity(self, report: ValidationReport) -> None:
        has_versions = bool(self.versions)
        has_overlays = self.has_overlays
        raw_matrix = self.raw_settings.get("matrix")
        has_matrix = bool(
            (isinstance(raw_matrix, Mapping) and raw_matrix)
            or (
                isinstance(raw_matrix, Sequence)
                and not isinstance(raw_matrix, (str, bytes, Mapping))
                and raw_matrix
            )
        )
        if has_versions and (has_overlays or has_matrix):
            SettingsBase.add_critical(
                report,
                "versions",
                "versions 不要和 overlays / matrix 同时写；选号是单独一种点名",
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
                suggested_fix='Set rolling to {"windows": [{"start": "20230101", "end": "20231231"}]}',
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
        if not isinstance(windows, Sequence) or isinstance(windows, (str, bytes)) or not windows:
            SettingsBase.add_critical(
                report,
                "rolling.windows",
                "attribution.rolling.windows 须为非空 list",
                suggested_fix='Set rolling.windows to [{"start": "20230101", "end": "20231231"}]',
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
        out["versions"] = list(self.versions)
        if self.is_select:
            out.pop("overlays", None)
            out.pop("matrix", None)
            return out
        if self.has_overlays:
            out["overlays"] = [row.to_dict() for row in self.overlays]
        else:
            out.pop("overlays", None)
        if not self.has_matrix:
            out.pop("matrix", None)
        return out
