"""Strategy settings 外层代理（与各 settings section 一一对应）。

消费者: scanner, enumerator, price_factor, portfolio
其它: hooks, core.services

本文件:
- StrategySettings: meta/data/sampling/goal/fees/simulation/portfolio/scanner 子配置 + merge/指纹字段
  边界: 负责 settings 对象化与 effective merge；不负责磁盘 discovery 或引擎执行
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple, Union

from core.infra.utils import Utils
from core.modules.backtest_engine.contracts import BacktestMode

from .analysis_settings import AnalysisSettings
from .execute_fp_whitelist import EXECUTE_NESTED_DROP_KEYS, EXECUTE_SETTINGS_FIELDS
from .data_settings import DataSettings
from .fees_settings import FeesSettings
from .goal_settings import GoalSettings
from .meta_settings import MetaSettings
from .portfolio_settings import PortfolioSettings
from .sampling_settings import SamplingSettings
from .scanner_settings import ScannerSettings
from .simulation_settings import BacktestPeriod, SimulationSettings
from .validation_report import ValidationReport


@dataclass
class StrategySettings:
    """Strategy settings proxy。

    内层子类与 settings section 一一对应（见模块 docstring）。
    """

    raw_settings: Dict[str, Any]
    _validated: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw_settings", copy.deepcopy(self.raw_settings))
        object.__setattr__(self, "meta", MetaSettings(raw_settings=self.raw_settings))
        object.__setattr__(self, "data", DataSettings(raw_settings=self.raw_settings))
        object.__setattr__(self, "sampling", SamplingSettings(raw_settings=self.raw_settings))
        object.__setattr__(self, "goal", GoalSettings(raw_settings=self.raw_settings))
        object.__setattr__(self, "fees", FeesSettings(raw_settings=self.raw_settings))
        object.__setattr__(
            self, "simulation", SimulationSettings(raw_settings=self.raw_settings)
        )
        object.__setattr__(
            self, "portfolio", PortfolioSettings(raw_settings=self.raw_settings)
        )
        object.__setattr__(self, "scanner", ScannerSettings(raw_settings=self.raw_settings))
        object.__setattr__(self, "analysis", AnalysisSettings(raw_settings=self.raw_settings))

    @classmethod
    def from_dict(cls, settings: Dict[str, Any]) -> "StrategySettings":
        return cls(raw_settings=copy.deepcopy(settings))

    @classmethod
    def diff(cls, disk_settings: Dict[str, Any], user_settings: Dict[str, Any]) -> Dict[str, Any]:
        return Utils.types.deep_diff(disk_settings, user_settings)

    @classmethod
    def _filter_fingerprint_fields(cls, diff: Dict[str, Any]) -> Dict[str, Any]:
        return {
            key: copy.deepcopy(value)
            for key, value in diff.items()
            if key.split(".")[0] in EXECUTE_SETTINGS_FIELDS
        }

    @classmethod
    def to_usable(
        cls,
        settings: Union["StrategySettings", Dict[str, Any], None],
    ) -> "StrategySettings":
        """clone → apply_defaults → validate。不能跑回测则无法给出身份。"""
        obj = cls.from_dict(cls._raw_settings_dict(settings))
        report = obj.validate()
        if not report.is_usable():
            raise ValueError(cls.format_validation_error(report))
        return obj

    @staticmethod
    def format_validation_error(report: ValidationReport) -> str:
        errors = list(getattr(report, "errors", None) or [])
        if not errors:
            return "settings 校验失败"
        first = errors[0]
        if isinstance(first, dict):
            field = str(
                first.get("field_path")
                or first.get("field")
                or first.get("path")
                or ""
            ).strip()
            msg = str(first.get("message") or first.get("msg") or "").strip()
            if field and msg:
                return f"settings 校验失败: {field}: {msg}"
            if msg:
                return f"settings 校验失败: {msg}"
        return f"settings 校验失败: {first}"

    @classmethod
    def extract_execute_settings(
        cls,
        settings: Union["StrategySettings", Dict[str, Any], None],
    ) -> Dict[str, Any]:
        """抽出 ``execute_fp`` 的 settings 块。

        先 ``to_usable``，再白名单 + 去草稿 + 去空对象。
        缺 key 与「显式写成默认值」会收敛成同一份投影。
        """
        raw = dict(cls.to_usable(settings).raw_settings)
        extracted: Dict[str, Any] = {}
        for key in sorted(EXECUTE_SETTINGS_FIELDS):
            if key not in raw or raw[key] is None:
                continue
            extracted[key] = copy.deepcopy(raw[key])
        return cls._prune_empty_objects(cls._drop_nested_keys(extracted))

    @staticmethod
    def _raw_settings_dict(
        settings: Union["StrategySettings", Dict[str, Any], None],
    ) -> Dict[str, Any]:
        if settings is None:
            return {}
        raw = getattr(settings, "raw_settings", None)
        if isinstance(raw, dict):
            return dict(raw)
        if isinstance(settings, dict):
            return dict(settings)
        return {}

    @classmethod
    def _drop_nested_keys(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: cls._drop_nested_keys(item)
                for key, item in value.items()
                if key not in EXECUTE_NESTED_DROP_KEYS
            }
        if isinstance(value, list):
            return [cls._drop_nested_keys(item) for item in value]
        return value

    @classmethod
    def _prune_empty_objects(cls, value: Any) -> Any:
        if isinstance(value, dict):
            out: Dict[str, Any] = {}
            for key, item in value.items():
                pruned = cls._prune_empty_objects(item)
                if isinstance(pruned, dict) and not pruned:
                    continue
                out[key] = pruned
            return out
        if isinstance(value, list):
            return [cls._prune_empty_objects(item) for item in value]
        return value

    @classmethod
    def fingerprint_diff(
        cls,
        disk_settings: Dict[str, Any],
        user_settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        return cls._filter_fingerprint_fields(cls.diff(disk_settings, user_settings))

    @classmethod
    def merge_disk_with_diff(
        cls,
        disk_settings: Dict[str, Any],
        settings_diff: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not settings_diff:
            return copy.deepcopy(disk_settings)
        return Utils.types.deep_merge(copy.deepcopy(disk_settings), settings_diff)

    @classmethod
    def calculate_effective_settings(
        cls,
        disk_settings: Dict[str, Any],
        user_settings: Dict[str, Any],
    ) -> Tuple["StrategySettings", Dict[str, Any]]:
        settings_diff = cls.fingerprint_diff(disk_settings, user_settings)
        effective = cls.merge_disk_with_diff(disk_settings, settings_diff)
        return cls(raw_settings=effective), settings_diff

    @property
    def execution_mode(self) -> str:
        sim = self.simulation
        sim.apply_defaults()
        raw = sim.mode
        if not raw:
            raise ValueError(
                f"settings.simulation.execution.mode 必填"
                f"（{BacktestMode.ENTITY_BASED.value} | {BacktestMode.SLICE_BASED.value}）"
            )
        return BacktestMode.normalize(raw)

    @property
    def start_date(self) -> str:
        return self.simulation.start_date

    @property
    def end_date(self) -> str:
        return self.simulation.end_date

    def resolve_period(self) -> BacktestPeriod:
        """回测前：补齐空 start/end 后的开市日区间。"""
        return self.simulation.resolve_period()

    @property
    def is_entity_based(self) -> bool:
        return self.execution_mode == BacktestMode.ENTITY_BASED.value

    @property
    def is_slice_based(self) -> bool:
        return self.execution_mode == BacktestMode.SLICE_BASED.value

    @property
    def is_enabled(self) -> bool:
        return bool(self.raw_settings.get("is_enabled", False))

    @property
    def key(self) -> str:
        return self.meta.key

    @property
    def display_name(self) -> str:
        return self.meta.display_name

    @property
    def core(self) -> Dict[str, Any]:
        """策略私有参数（无专用 dataclass，直接读 raw）。"""
        block = self.raw_settings.get("core")
        return dict(block) if isinstance(block, dict) else {}

    def apply_defaults(self) -> None:
        if "is_enabled" not in self.raw_settings:
            self.raw_settings["is_enabled"] = False
        self.meta.apply_defaults()
        self.data.apply_defaults()
        self.sampling.apply_defaults()
        self.goal.apply_defaults()
        self.fees.apply_defaults()
        self.simulation.apply_defaults()
        self.portfolio.apply_defaults()
        self.scanner.apply_defaults()
        self.analysis.apply_defaults()

    def validate(self) -> ValidationReport:
        report = ValidationReport(is_valid=True)
        self.apply_defaults()

        from .settings_base import SettingsBase

        if not isinstance(self.raw_settings.get("is_enabled"), bool):
            SettingsBase.add_warning(
                report,
                "is_enabled",
                "is_enabled should be bool",
                suggested_fix="Set is_enabled to true or false",
            )

        for sub in (
            self.meta,
            self.data,
            self.sampling,
            self.goal,
            self.fees,
            self.simulation,
            self.portfolio,
            self.scanner,
            self.analysis,
        ):
            sub_report = sub.validate()
            report.errors.extend(sub_report.errors)
            report.warnings.extend(sub_report.warnings)
            if not sub_report.is_valid:
                report.is_valid = False

        self._validated = report.is_usable()
        return report

    def is_valid(self) -> bool:
        return bool(self._validated)

    def to_dict(self) -> Dict[str, Any]:
        """展开默认值的拷贝；不得改 ``self.raw_settings``（否则会污染 execute_fp / 归档）。"""
        clone = StrategySettings(raw_settings=copy.deepcopy(self.raw_settings))
        clone.apply_defaults()
        out = copy.deepcopy(clone.raw_settings)
        out["is_enabled"] = clone.is_enabled
        out["meta"] = clone.meta.to_dict()
        if clone.core:
            out["core"] = clone.core
        out["data"] = clone.data.to_dict()
        sampling = clone.sampling.to_dict()
        if sampling:
            out["sampling"] = sampling
        out["goal"] = clone.goal.to_dict()
        if clone.fees.fees:
            out["fees"] = clone.fees.to_dict()
        out["simulation"] = {
            **(clone.raw_settings.get("simulation") or {}),
            **clone.simulation.to_dict(),
        }
        if clone.portfolio.portfolio:
            out["portfolio"] = clone.portfolio.to_dict()
        if clone.scanner.scanner:
            out["scanner"] = clone.scanner.to_dict()
        if clone.analysis.enabled or "analysis" in clone.raw_settings:
            out["analysis"] = clone.analysis.to_dict()
        return out


__all__ = ["StrategySettings"]
