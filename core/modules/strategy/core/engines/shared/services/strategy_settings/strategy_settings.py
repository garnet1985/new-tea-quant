"""Strategy settings 外层代理（与各 settings section 一一对应）。

消费者: scanner, enumerator, price_factor, portfolio
其它: hooks, core.services

本文件:
- StrategySettings: meta/data/sampling/goal/fees/simulation/portfolio/scanner 子配置 + merge/指纹字段
  边界: 负责 settings 对象化与 effective merge；不负责磁盘 discovery 或引擎执行
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, FrozenSet, List, Tuple

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from .meta_settings import MetaSettings
from .data_settings import DataSettings
from .sampling_settings import SamplingSettings
from .goal_settings import GoalSettings
from .fees_settings import FeesSettings
from .simulation_settings import BacktestPeriod, SimulationSettings
from .portfolio_settings import PortfolioSettings
from .scanner_settings import ScannerSettings
from .validation_report import ValidationReport
from core.infra.utils import Utils


@dataclass
class StrategySettings:
    """Strategy settings proxy。

    内层子类与 settings section 一一对应（见模块 docstring）。
    """

    FINGERPRINT_FIELDS: ClassVar[FrozenSet[str]] = frozenset(
        {
            "core",
            "data",
            "goal",
            "sampling",
            "fees",
            "simulation",
            "portfolio",
            "market_profile",
        }
    )

    NON_FINGERPRINT_FIELDS: ClassVar[FrozenSet[str]] = frozenset(
        {
            "meta",
            "is_enabled",
            "scanner",
            "enumerator",
        }
    )

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
            if key.split(".")[0] in cls.FINGERPRINT_FIELDS
        }

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

    @classmethod
    def fingerprint_payload(cls, settings_diff: Dict[str, Any]) -> Dict[str, Any]:
        return copy.deepcopy(settings_diff)

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

    def fingerprint_hash(
        self,
        *,
        settings_diff: Dict[str, Any],
        entity_ids: List[str],
        start_date: str,
        end_date: str,
    ) -> str:
        signature = {
            "settings": self.fingerprint_payload(settings_diff),
            "entity_ids": sorted(entity_ids),
            "start_date": start_date,
            "end_date": end_date,
        }
        return self._stable_hash(signature)

    @staticmethod
    def _stable_hash(payload: Dict[str, Any]) -> str:
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

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
        self.apply_defaults()
        out = copy.deepcopy(self.raw_settings)
        out["is_enabled"] = self.is_enabled
        out["meta"] = self.meta.to_dict()
        if self.core:
            out["core"] = self.core
        out["data"] = self.data.to_dict()
        sampling = self.sampling.to_dict()
        if sampling:
            out["sampling"] = sampling
        out["goal"] = self.goal.to_dict()
        if self.fees.fees:
            out["fees"] = self.fees.to_dict()
        out["simulation"] = {
            **(self.raw_settings.get("simulation") or {}),
            **self.simulation.to_dict(),
        }
        if self.portfolio.portfolio:
            out["portfolio"] = self.portfolio.to_dict()
        if self.scanner.scanner:
            out["scanner"] = self.scanner.to_dict()
        return out


__all__ = ["StrategySettings"]
