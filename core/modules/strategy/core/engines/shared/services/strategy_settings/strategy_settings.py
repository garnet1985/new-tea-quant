"""Strategy settings proxy (shell/container for all sub-settings)."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, FrozenSet, List, Tuple

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.utils.utils import Utils

from .general_settings import GeneralSettings
from .enumerator_settings import EnumeratorSettings
from .data_settings import DataSettings
from .simulation_settings import SimulationSettings
from .validation_report import ValidationReport


@dataclass
class StrategySettings:
    """Strategy settings proxy (shell/container for all sub-settings).

    2层结构：
    - 外层：StrategySettings（proxy/壳子）
    - 内层：GeneralSettings、EnumeratorSettings等子配置类

    磁盘 settings 与用户覆盖的 diff / merge 也在此类上完成。
    """

    FINGERPRINT_FIELDS: ClassVar[FrozenSet[str]] = frozenset(
        {
            "core",
            "data",
            "goal",
            "sampling",
            "price_simulator",
            "capital_simulator",
            "fees",
            "simulation",
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
        """Post-init: deep copy raw_settings and create sub-settings."""
        object.__setattr__(self, 'raw_settings', copy.deepcopy(self.raw_settings))
        object.__setattr__(self, 'general', GeneralSettings(raw_settings=self.raw_settings))
        object.__setattr__(self, 'enumerator', EnumeratorSettings(raw_settings=self.raw_settings))
        object.__setattr__(self, 'data', DataSettings(raw_settings=self.raw_settings))
        object.__setattr__(self, 'simulation', SimulationSettings(raw_settings=self.raw_settings))

    @classmethod
    def from_dict(cls, settings: Dict[str, Any]) -> "StrategySettings":
        """从 settings dict 构建 StrategySettings。"""
        return cls(raw_settings=copy.deepcopy(settings))

    @classmethod
    def diff(cls, disk_settings: Dict[str, Any], user_settings: Dict[str, Any]) -> Dict[str, Any]:
        """磁盘 vs 用户的完整 diff。"""
        return Utils.deep_diff(disk_settings, user_settings)

    @classmethod
    def _filter_fingerprint_fields(cls, diff: Dict[str, Any]) -> Dict[str, Any]:
        """只保留影响回测结果的 diff 字段。"""
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
        """disk vs user 的 diff，仅保留影响回测/指纹的字段。"""
        return cls._filter_fingerprint_fields(cls.diff(disk_settings, user_settings))

    @classmethod
    def merge_disk_with_diff(
        cls,
        disk_settings: Dict[str, Any],
        settings_diff: Dict[str, Any],
    ) -> Dict[str, Any]:
        """磁盘基准 + diff → 有效 settings dict。"""
        if not settings_diff:
            return copy.deepcopy(disk_settings)
        return Utils.deep_merge(copy.deepcopy(disk_settings), settings_diff)

    @classmethod
    def calculate_effective_settings(
        cls,
        disk_settings: Dict[str, Any],
        user_settings: Dict[str, Any],
    ) -> Tuple["StrategySettings", Dict[str, Any]]:
        """disk + user 覆盖 → (有效 StrategySettings, fingerprint_diff)。

        Args:
            disk_settings: 磁盘上的settings（基准）
            user_settings: 用户修改的settings（覆盖）

        Returns:
            (merged_settings, settings_diff)元组
            - merged_settings: 合并后的有效settings（StrategySettings对象）
            - settings_diff: 影响回测结果的差异字段（只包含FINGERPRINT_FIELDS）
        """
        settings_diff = cls.fingerprint_diff(disk_settings, user_settings)
        effective = cls.merge_disk_with_diff(disk_settings, settings_diff)
        return cls(raw_settings=effective), settings_diff

    @classmethod
    def fingerprint_payload(cls, settings_diff: Dict[str, Any]) -> Dict[str, Any]:
        """用于指纹计算的 settings 片段。"""
        return copy.deepcopy(settings_diff)

    @property
    def execution_mode(self) -> str:
        """BacktestEngine 模式名（``simulation.execution_mode``）。"""
        simulation = self.raw_settings.get("simulation")
        if not isinstance(simulation, dict):
            raise ValueError("settings.simulation 须为 dict")
        raw = simulation.get("execution_mode")
        if raw is None or str(raw).strip() == "":
            raise ValueError(
                f"settings.simulation.execution_mode 必填"
                f"（{BacktestMode.ENTITY_BASED.value} | {BacktestMode.SLICE_BASED.value}）"
            )
        return BacktestMode.normalize(raw)

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
        """枚举指纹（settings_diff + entity_ids + 日期区间）。"""
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
        """Get is_enabled flag."""
        return self.general.is_enabled

    @property
    def key(self) -> str:
        """Get module key from meta."""
        return self.general.key

    @property
    def display_name(self) -> str:
        """Get display name."""
        return self.general.display_name

    def apply_defaults(self) -> None:
        """Apply defaults to all sub-settings."""
        self.general.apply_defaults()
        self.enumerator.apply_defaults()
        self.data.apply_defaults()
        self.simulation.apply_defaults()

    def validate(self) -> ValidationReport:
        """Validate all sub-settings."""
        report = ValidationReport(is_valid=True)

        # Validate general
        general_report = self.general.validate()
        report.errors.extend(general_report.errors)
        report.warnings.extend(general_report.warnings)
        if not general_report.is_valid:
            report.is_valid = False

        # Validate enumerator
        enum_report = self.enumerator.validate()
        report.errors.extend(enum_report.errors)
        report.warnings.extend(enum_report.warnings)
        if not enum_report.is_valid:
            report.is_valid = False

        data_report = self.data.validate()
        report.errors.extend(data_report.errors)
        report.warnings.extend(data_report.warnings)
        if not data_report.is_valid:
            report.is_valid = False

        simulation_report = self.simulation.validate()
        report.errors.extend(simulation_report.errors)
        report.warnings.extend(simulation_report.warnings)
        if not simulation_report.is_valid:
            report.is_valid = False

        self._validated = report.is_usable()
        return report

    def is_valid(self) -> bool:
        """Check if settings is valid."""
        return bool(self._validated)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict."""
        self.apply_defaults()
        out = copy.deepcopy(self.raw_settings)
        out['is_enabled'] = self.is_enabled
        out['meta'] = self.general.meta
        out['core'] = self.general.core
        out['data'] = self.data.to_dict()
        out['enumerator'] = self.enumerator.to_dict()
        out['simulation'] = {**self.raw_settings.get('simulation', {}), **self.simulation.to_dict()}
        return out


__all__ = ['StrategySettings']