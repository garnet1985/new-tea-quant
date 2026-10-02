"""``attribution.py`` 战役外壳（versions / overlays / matrix / rolling）。

层由 CLI（sea / spa / soa）选定，本文件不再读 ``steps``。
和 ``settings.py`` 一样：raw dict → dataclass → ``apply_defaults`` / ``validate``。
不进 execute_fp / env_fp。``overlays`` 是逐项对照；``matrix`` 是各轴笛卡尔积。
二者可同时写，各自成表；只有回测执行按身份去重。rolling.windows 是区间，报告仍分开写。
"""
from __future__ import annotations

import copy
import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple, Union

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
from core.modules.strategy.core.services.discovery.path_rules import StrategyPathRules

from .grid import SettingsMatrix
from .overlay import SettingsOverlay

ATTRIBUTION_FILE_NAME = "attribution.py"

_ALLOWED_STEPS = frozenset(k.value for k in SimulateKind)


@dataclass
class AttributionSettings(SettingsBase):
    """战役配置代理。section 只有这一层；逐项见 ``SettingsOverlay``，交叉见 ``SettingsMatrix``。"""

    raw_settings: Dict[str, Any]
    _validated: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        self.raw_settings = copy.deepcopy(self.raw_settings)

    @classmethod
    def from_dict(cls, settings: Mapping[str, Any]) -> "AttributionSettings":
        if not isinstance(settings, Mapping):
            raise ValueError("attribution 须为 dict")
        return cls(raw_settings=dict(settings))

    @classmethod
    def load(
        cls,
        strategy_folder: Path,
        *,
        strategy_key: Optional[str] = None,
    ) -> "AttributionSettings":
        return cls.to_usable(
            cls._load_dict_from_folder(strategy_folder, strategy_key=strategy_key)
        )

    @classmethod
    def _load_dict_from_folder(
        cls,
        strategy_folder: Path,
        *,
        strategy_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        folder = Path(strategy_folder)
        attr_file = folder / ATTRIBUTION_FILE_NAME
        if not attr_file.is_file():
            raise FileNotFoundError(f"attribution.py not found: {attr_file}")

        key = str(strategy_key or folder.name).strip() or folder.name
        module_name = StrategyPathRules.strategy_module_id(key, suffix="attribution")
        spec = importlib.util.spec_from_file_location(module_name, attr_file)
        if spec is None or spec.loader is None:
            raise ValueError(f"cannot load attribution module: {attr_file}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = getattr(module, "attribution", None)
        if not isinstance(payload, dict):
            raise ValueError(f"attribution.py 必须定义 dict attribution: {attr_file}")
        return dict(payload)

    @classmethod
    def to_usable(
        cls,
        settings: Union[Mapping[str, Any], "AttributionSettings", None],
    ) -> "AttributionSettings":
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
        """``rolling`` 块；层由 CLI / RollingPipeline 决定，不再读 steps。"""
        block = self.raw_settings.get("rolling")
        nested = dict(block) if isinstance(block, Mapping) else {}
        nested.pop("steps", None)
        return nested

    @property
    def simulate_kind(self) -> SimulateKind:
        """兼容旧报告字段；层实际由 sea/spa/soa 决定。"""
        return SimulateKind.PORTFOLIO

    def apply_defaults(self) -> None:
        self.raw_settings.pop("fill_missing", None)
        self.raw_settings.pop("steps", None)
        rolling = self.raw_settings.get("rolling")
        if isinstance(rolling, dict):
            rolling.pop("fill_missing", None)
            rolling.pop("steps", None)
        if self.raw_settings.get("versions") is None:
            self.raw_settings["versions"] = []

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        self.apply_defaults()

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
            raw_versions = []
        else:
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
            raw_overlays = []
        else:
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

        SettingsMatrix.validate(self.raw_settings.get("matrix"), report)

        has_versions = bool(
            isinstance(self.raw_settings.get("versions"), Sequence)
            and not isinstance(self.raw_settings.get("versions"), (str, bytes))
            and self.raw_settings.get("versions")
        )
        has_overlays = bool(
            isinstance(self.raw_settings.get("overlays"), Sequence)
            and not isinstance(self.raw_settings.get("overlays"), (str, bytes))
            and self.raw_settings.get("overlays")
        )
        raw_matrix = self.raw_settings.get("matrix")
        has_matrix = bool(
            (isinstance(raw_matrix, Mapping) and raw_matrix)
            or (
                isinstance(raw_matrix, Sequence)
                and not isinstance(raw_matrix, (str, bytes, Mapping))
                and raw_matrix
            )
        )
        chosen = [
            name
            for name, flag in (
                ("versions", has_versions),
                ("overlays", has_overlays),
                ("matrix", has_matrix),
            )
            if flag
        ]
        if has_versions and (has_overlays or has_matrix):
            SettingsBase.add_critical(
                report,
                "versions",
                "versions 不要和 overlays / matrix 同时写；选号是单独一种点名",
            )
        has_rolling = self._validate_rolling(report)
        if not chosen and not has_rolling:
            SettingsBase.add_critical(
                report,
                "overlays",
                "versions、overlays、matrix、rolling.windows 不能都空",
                suggested_fix="写 overlays 做逐项对照，matrix 做交叉网格（可同时写），versions 选号，或 rolling.windows 做滚动",
            )

        self._validated = report.is_usable()
        return report

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
                suggested_fix="rolling 只放 windows；steps 可省略（继承顶层）",
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
