#!/usr/bin/env python3
"""策略 settings 数据类包入口。"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict

from .fees_settings import StrategyFeesSettings
from .settings_base import SettingsBase, ValidationReport


@dataclass
class StrategySettings(SettingsBase):
    raw_settings: Dict[str, Any]
    _validated: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "raw_settings", copy.deepcopy(self.raw_settings))
        rs = self.raw_settings
        from .data_settings import StrategyDataSettings
        from .goal_settings import StrategyGoalSettings
        from .meta_settings import StrategyMetaSettings
        from .sampling_settings import StrategySamplingSettings
        from core.modules.strategy.engines.scanner.data_classes.settings import (
            StrategyScannerSettings,
        )
        from core.modules.strategy.engines.simulator.capital_allocation.data_classes.settings import (
            StrategyCapitalSimulatorSettings,
        )
        from core.modules.strategy.engines.simulator.enumerator.data_classes.strategy_settings import (
            StrategyEnumeratorSettings,
        )
        from core.modules.strategy.engines.simulator.price_factor.data_classes.settings import (
            StrategyPriceSimulatorSettings,
        )

        object.__setattr__(self, "meta", StrategyMetaSettings.from_raw(rs))
        object.__setattr__(self, "fees", StrategyFeesSettings.from_strategy_root(rs))
        object.__setattr__(self, "data", StrategyDataSettings.from_strategy_root(rs))
        object.__setattr__(self, "sampling", StrategySamplingSettings.from_strategy_root(rs))
        object.__setattr__(self, "goal", StrategyGoalSettings.from_strategy_root(rs))
        object.__setattr__(self, "enumerator", StrategyEnumeratorSettings.from_strategy_root(rs))
        object.__setattr__(self, "price_simulator", StrategyPriceSimulatorSettings.from_strategy_root(rs))
        object.__setattr__(self, "capital_simulator", StrategyCapitalSimulatorSettings.from_strategy_root(rs))
        object.__setattr__(self, "scanner", StrategyScannerSettings.from_strategy_root(rs))

    @property
    def strategy_name(self) -> str:
        return str(self.meta.name)

    @property
    def is_enabled(self) -> bool:
        return bool(self.meta.is_enabled)

    def apply_defaults(self) -> None:
        rs = self.raw_settings
        self.meta.apply_defaults()
        rs["name"] = self.meta.name
        rs["description"] = self.meta.description
        rs["core"] = self.meta.core
        rs["is_enabled"] = self.meta.is_enabled
        self.fees.apply_defaults()
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
        self.apply_defaults()
        merged = SettingsBase.merge_validation_results(
            self.meta.validate(),
            self.fees.validate(),
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
        return bool(self._validated)

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        out = self.deep_copy_dict(self.raw_settings)
        # API/BFF 有时会同时带根级 name/description 与嵌套 meta；引擎语义只用根级（见 meta.to_dict）。
        out.pop("meta", None)
        out.update(self.meta.to_dict())
        out["fees"] = self.fees.to_dict()
        out["data"] = self.data.to_dict()
        out["sampling"] = self.sampling.to_dict()
        out["goal"] = self.goal.to_dict()
        out["enumerator"] = self.enumerator.to_dict()
        out["price_simulator"] = self.price_simulator.to_dict()
        out["capital_simulator"] = self.capital_simulator.to_dict()
        out["scanner"] = self.scanner.to_dict()
        return out

    def settings_core_for_fingerprint(self) -> Dict[str, Any]:
        """
        在已通过校验、默认已补足的 settings 上，剔除非语义字段，得到用于指纹的 settings_core。
        若当前配置校验失败则抛出 ValueError。
        """
        from .settings_fingerprint_core import strip_fingerprint_non_core

        report = self.validate()
        if not report.is_usable():
            errs = [
                f'{item.get("field_path", "?")}: {item.get("message", "")}'
                for item in (report.errors or [])
                if item.get("level") == "critical"
            ]
            detail = "；".join(errs) if errs else "settings 校验未通过，无法构建指纹"
            raise ValueError(detail)
        return strip_fingerprint_non_core(self.to_dict())

    @classmethod
    def build_settings_core_for_fingerprint(cls, raw_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        从原始 settings dict 构建指纹用 settings_core：内部先 `StrategySettings.validate()` + `to_dict()`，
        再按 `settings_fingerprint_core` 忽略表剔除。
        """
        inst = cls(raw_settings=dict(raw_settings or {}))
        return inst.settings_core_for_fingerprint()

    def to_enum_signature_dict(self) -> Dict[str, Any]:
        normalized = self.to_dict()
        return {
            "name": normalized.get("name", ""),
            "core": normalized.get("core", {}) or {},
            "data": normalized.get("data", {}) or {},
            "goal": normalized.get("goal", {}) or {},
            "enumerator": normalized.get("enumerator", {}) or {},
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
        return self._stable_hash(self.to_enum_signature_dict())

    def is_enum_settings_same(self, other: Any) -> bool:
        if isinstance(other, StrategySettings):
            return self.enum_signature_hash() == other.enum_signature_hash()
        if isinstance(other, dict):
            other_settings = StrategySettings(raw_settings=dict(other))
            return self.enum_signature_hash() == other_settings.enum_signature_hash()
        return False


BaseSettings = StrategySettings

from .data_settings import StrategyDataSettings  # noqa: E402
from .goal_settings import StrategyGoalSettings  # noqa: E402
from .meta_settings import StrategyMetaSettings  # noqa: E402
from .sampling_settings import StrategySamplingSettings  # noqa: E402
from core.modules.strategy.engines.scanner.data_classes.settings import (  # noqa: E402
    ScannerSettings,
    StrategyScannerSettings,
)
from core.modules.strategy.engines.simulator.capital_allocation.data_classes.settings import (  # noqa: E402
    AllocationConfig,
    CapitalAllocationSettings,
    OutputConfig,
    StrategyCapitalSimulatorSettings,
)
from core.modules.strategy.engines.simulator.enumerator.data_classes.strategy_settings import (  # noqa: E402
    EnumeratorSettings,
    StrategyEnumeratorSettings,
)
from core.modules.strategy.engines.simulator.price_factor.data_classes.settings import (  # noqa: E402
    StrategyPriceFactorSimulationSettings,
    StrategyPriceSimulatorSettings,
)

__all__ = [
    "AllocationConfig",
    "BaseSettings",
    "CapitalAllocationSettings",
    "EnumeratorSettings",
    "OutputConfig",
    "StrategyDataSettings",
    "StrategyFeesSettings",
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
