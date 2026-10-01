"""``attribution.py`` 战役外壳（steps / versions|matrix / rolling）。

和 ``settings.py`` 一样：raw dict → dataclass → ``apply_defaults`` / ``validate``。
不进 execute_fp / env_fp。matrix 行是稀疏 overlay；rolling.windows 是区间，报告仍分开写。
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

from .overlay import SettingsOverlay

ATTRIBUTION_FILE_NAME = "attribution.py"

_ALLOWED_STEPS = frozenset(k.value for k in SimulateKind)


@dataclass
class AttributionSettings(SettingsBase):
    """战役配置代理。section 只有这一层；matrix 元素见 ``SettingsOverlay``。"""

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
    def matrix(self) -> Tuple[SettingsOverlay, ...]:
        raw = self.raw_settings.get("matrix")
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
            return ()
        return tuple(
            SettingsOverlay.from_dict(row)
            for row in raw
            if isinstance(row, Mapping)
        )

    @property
    def is_select(self) -> bool:
        return bool(self.versions)

    @property
    def has_parameter(self) -> bool:
        return bool(self.versions) or bool(self.matrix)

    def rolling_payload(self) -> Dict[str, Any]:
        """顶层 steps 与 ``rolling`` 块合并，给滚动任务用。"""
        block = self.raw_settings.get("rolling")
        nested = dict(block) if isinstance(block, Mapping) else {}
        out: Dict[str, Any] = {
            "steps": list(self.raw_settings.get("steps") or []),
        }
        out.update(nested)
        return out

    @property
    def simulate_kind(self) -> SimulateKind:
        """steps 最后一步：选号 lookup 用。matrix 格按 ``steps`` 逐层 simulate。

        ``simulate(kind=portfolio)`` 只保证枚举依赖，不会自动跑 price_factor。
        """
        steps = self.steps
        if not steps:
            raise ValueError("attribution.steps 不能为空")
        return steps[-1]

    def apply_defaults(self) -> None:
        self.raw_settings.pop("fill_missing", None)
        rolling = self.raw_settings.get("rolling")
        if isinstance(rolling, dict):
            rolling.pop("fill_missing", None)
        if self.raw_settings.get("versions") is None:
            self.raw_settings["versions"] = []

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

        raw_matrix = self.raw_settings.get("matrix")
        if raw_matrix is None:
            raw_matrix = []
        if not isinstance(raw_matrix, Sequence) or isinstance(raw_matrix, (str, bytes)):
            SettingsBase.add_critical(
                report,
                "matrix",
                "attribution.matrix 须为 list",
                suggested_fix="Set matrix to a list of overlay dicts or []",
            )
            raw_matrix = []
        else:
            for i, row in enumerate(raw_matrix):
                if not isinstance(row, Mapping) or not row:
                    SettingsBase.add_critical(
                        report,
                        f"matrix[{i}]",
                        "须为非空 dict overlay",
                    )
                    continue
                overlay_report = SettingsOverlay.from_dict(row).validate()
                for err in overlay_report.errors:
                    err = dict(err)
                    err["field_path"] = f"matrix[{i}].{err.get('field_path') or ''}".rstrip(".")
                    report.errors.append(err)
                    report.is_valid = False

        has_versions = bool(
            isinstance(self.raw_settings.get("versions"), Sequence)
            and not isinstance(self.raw_settings.get("versions"), (str, bytes))
            and self.raw_settings.get("versions")
        )
        has_matrix = bool(
            isinstance(self.raw_settings.get("matrix"), Sequence)
            and not isinstance(self.raw_settings.get("matrix"), (str, bytes))
            and self.raw_settings.get("matrix")
        )
        if has_versions and has_matrix:
            SettingsBase.add_critical(
                report,
                "versions",
                "versions 与 matrix 不要同时写；versions 非空即选号",
            )
        has_rolling = self._validate_rolling(report)
        if not has_versions and not has_matrix and not has_rolling:
            SettingsBase.add_critical(
                report,
                "matrix",
                "versions、matrix、rolling.windows 不能都空",
                suggested_fix="写 matrix / versions 做参数战役，或写 rolling.windows 做滚动验证",
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
        out["steps"] = [k.value for k in self.steps]
        out["versions"] = list(self.versions)
        if self.is_select:
            out.pop("matrix", None)
        else:
            out["matrix"] = [row.to_dict() for row in self.matrix]
        return out
