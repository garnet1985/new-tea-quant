#!/usr/bin/env python3
"""
策略 settings 数据类包入口。

``StrategySettings``（本模块内定义）：接收用户 dict，**构造时**实例化各章 dataclass，并统一调度
``apply_defaults`` / ``validate``（仅发现等入口调用一次）/ ``to_dict``。

各章 ``Strategy*Settings`` 由同包其他模块提供，见下方 re-export。
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict

from .settings_base import SettingsBase, ValidationReport


@dataclass
class StrategySettings(SettingsBase):
    """
    顶层策略配置：``raw_settings`` 为深拷贝后的整包 dict；各章实例在构造时建好，与子树共享引用。

    只读语义：外部勿改 ``raw_settings`` 与子章内部 dict；需要新视图请 ``to_dict()``。
    """

    raw_settings: Dict[str, Any]
    _validated: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw_settings", copy.deepcopy(self.raw_settings))
        rs = self.raw_settings

        from .capital_allocation_settings import StrategyCapitalSimulatorSettings
        from .data_settings import StrategyDataSettings
        from .enumerator_settings import StrategyEnumeratorSettings
        from .goal_settings import StrategyGoalSettings
        from .meta_settings import StrategyMetaSettings
        from .price_simulation_settings import StrategyPriceSimulatorSettings
        from .sampling_settings import StrategySamplingSettings
        from .scanner_settings import StrategyScannerSettings

        object.__setattr__(self, "meta", StrategyMetaSettings.from_raw(rs))
        object.__setattr__(self, "data", StrategyDataSettings.from_strategy_root(rs))
        object.__setattr__(self, "sampling", StrategySamplingSettings.from_strategy_root(rs))
        object.__setattr__(self, "goal", StrategyGoalSettings.from_strategy_root(rs))
        object.__setattr__(self, "enumerator", StrategyEnumeratorSettings.from_strategy_root(rs))
        object.__setattr__(
            self, "price_simulator", StrategyPriceSimulatorSettings.from_strategy_root(rs)
        )
        object.__setattr__(
            self, "capital_simulator", StrategyCapitalSimulatorSettings.from_strategy_root(rs)
        )
        object.__setattr__(self, "scanner", StrategyScannerSettings.from_strategy_root(rs))

    @property
    def strategy_name(self) -> str:
        return str(self.meta.name)

    @property
    def is_enabled(self) -> bool:
        return bool(self.meta.is_enabled)

    def apply_defaults(self) -> None:
        """依次调用各章 ``apply_defaults``，并把 meta 写回 ``raw_settings``。"""
        rs = self.raw_settings

        self.meta.apply_defaults()
        rs["name"] = self.meta.name
        rs["description"] = self.meta.description
        rs["core"] = self.meta.core
        rs["is_enabled"] = self.meta.is_enabled

        if "fees" not in rs or not isinstance(rs.get("fees"), dict):
            rs["fees"] = {}

        self.data.apply_defaults()
        self.sampling.apply_defaults()
        self.goal.apply_defaults()
        self.enumerator.apply_defaults()
        self.price_simulator.apply_defaults()
        self.capital_simulator.apply_defaults()
        self.scanner.apply_defaults()

    def validate(self) -> ValidationReport:
        return self.validate_base_settings()

    def validate_base_settings(self) -> ValidationReport:
        """合并各章 ``validate()`` 结果。"""
        self.apply_defaults()
        merged = SettingsBase.merge_validation_results(
            self.meta.validate(),
            self.data.validate(),
            self.sampling.validate(),
            self.goal.validate(),
            self.enumerator.validate(),
            self.price_simulator.validate(),
            self.capital_simulator.validate(),
            self.scanner.validate(),
        )
        self._validated = merged.is_usable()
        return merged

    def is_valid(self) -> bool:
        """是否已通过 ``validate()``（本模块内假定发现路径已调用，不再隐式重跑校验）。"""
        return bool(self._validated)

    def to_dict(self) -> Dict[str, Any]:
        """整包权威 dict：以 ``raw_settings`` 深拷贝为底，用各章 ``to_dict()`` 覆盖对应块。"""
        self.apply_defaults()
        out = self.deep_copy_dict(self.raw_settings)
        out.update(self.meta.to_dict())
        out["data"] = self.data.to_dict()
        out["sampling"] = self.sampling.to_dict()
        out["goal"] = self.goal.to_dict()
        out["enumerator"] = self.enumerator.to_dict()
        out["price_simulator"] = self.price_simulator.to_dict()
        out["capital_simulator"] = self.capital_simulator.to_dict()
        out["scanner"] = self.scanner.to_dict()
        return out

    def to_enum_signature_dict(self) -> Dict[str, Any]:
        """
        提取“会影响枚举结果”的配置签名（用于复用判断）。

        说明：
        - 这里不使用完整 settings，避免 description 等无关字段导致误判。
        - 以 apply_defaults + to_dict 后的数据为准，确保比较前先归一化。
        """
        normalized = self.to_dict()
        return {
            "name": normalized.get("name", ""),
            "core": normalized.get("core", {}) or {},
            "data": normalized.get("data", {}) or {},
            "goal": normalized.get("goal", {}) or {},
            "enumerator": normalized.get("enumerator", {}) or {},
            # sampling/scanner 在部分模式下会影响枚举输入，纳入签名更稳妥。
            "sampling": normalized.get("sampling", {}) or {},
            "scanner": normalized.get("scanner", {}) or {},
        }

    @staticmethod
    def _stable_hash(payload: Dict[str, Any]) -> str:
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def enum_signature_hash(self) -> str:
        """当前 settings 的枚举签名 hash（sha256）。"""
        return self._stable_hash(self.to_enum_signature_dict())

    def is_enum_settings_same(self, other: Any) -> bool:
        """
        判断“枚举相关配置”是否一致。

        支持：
        - StrategySettings 实例
        - 原始 settings dict
        """
        if isinstance(other, StrategySettings):
            return self.enum_signature_hash() == other.enum_signature_hash()

        if isinstance(other, dict):
            other_settings = StrategySettings(raw_settings=dict(other))
            return self.enum_signature_hash() == other_settings.enum_signature_hash()

        return False


BaseSettings = StrategySettings

from .capital_allocation_settings import (
    AllocationConfig,
    CapitalAllocationSettings,
    OutputConfig,
    StrategyCapitalSimulatorSettings,
)
from .data_settings import StrategyDataSettings
from .enumerator_settings import EnumeratorSettings, StrategyEnumeratorSettings
from .goal_settings import StrategyGoalSettings
from .meta_settings import StrategyMetaSettings
from .price_simulation_settings import (
    StrategyPriceFactorSimulationSettings,
    StrategyPriceSimulatorSettings,
)
from .sampling_settings import StrategySamplingSettings
from .scanner_settings import ScannerSettings, StrategyScannerSettings

__all__ = [
    "AllocationConfig",
    "BaseSettings",
    "CapitalAllocationSettings",
    "EnumeratorSettings",
    "OutputConfig",
    "StrategyDataSettings",
    "StrategyEnumeratorSettings",
    "StrategyGoalSettings",
    "StrategyCapitalSimulatorSettings",
    "StrategyMetaSettings",
    "StrategyPriceFactorSimulationSettings",
    "StrategyPriceSimulatorSettings",
    "StrategySettings",
    "ScannerSettings",
    "StrategySamplingSettings",
    "StrategyScannerSettings",
    "SettingsBase",
    "ValidationReport",
]
