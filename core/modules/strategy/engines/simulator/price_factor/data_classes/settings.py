#!/usr/bin/env python3
"""Price simulator settings data class."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, Literal, Union
from typing import TYPE_CHECKING

from core.modules.strategy.engines.shared.data_classes.strategy_settings.settings_base import (
    SettingsBase,
    ValidationReport,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
        StrategySettings,
    )


@dataclass
class StrategyPriceSimulatorSettings(SettingsBase):
    raw_settings: Dict[str, Any]
    _price_simulator_validated: bool = field(default=False, repr=False)

    @property
    def price_simulator(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "price_simulator")

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> "StrategyPriceSimulatorSettings":
        if not isinstance(root, dict):
            root = {}
        SettingsBase.ensure_dict_block(root, "price_simulator")
        return cls(raw_settings=root)

    @classmethod
    def from_base_settings(cls, base_settings: StrategySettings) -> "StrategyPriceSimulatorSettings":
        return cls.from_strategy_root(base_settings.raw_settings)

    def apply_defaults(self) -> None:
        ps = self.price_simulator
        if "base_version" not in ps and "output_version" in ps:
            ps["base_version"] = ps.get("output_version") or "latest"
        ps.setdefault("base_version", "latest")
        ps.setdefault("max_workers", "auto")

    def validate(self) -> ValidationReport:
        result = SettingsBase.new_validation()
        self.apply_defaults()

        bv = str(self.price_simulator.get("base_version") or "latest")
        if bv != "latest":
            SettingsBase.add_warning(result, "price_simulator.base_version", f"指定 base_version={bv}")
        self._validate_max_workers(result)
        SettingsBase.log_warnings(result, logger)
        self._price_simulator_validated = True
        return result

    def _validate_max_workers(self, result: ValidationReport) -> None:
        ps = self.price_simulator
        SettingsBase.validate_max_workers_field(
            report=result,
            container=ps,
            key="max_workers",
            field_path="price_simulator.max_workers",
            invalid_message='price_simulator.max_workers 须为 "auto" 或正整数',
        )

    def to_dict(self) -> Dict[str, Any]:
        out = self.deep_copy_dict(dict(self.price_simulator))
        for key in ("use_sampling", "start_date", "end_date", "fees"):
            out.pop(key, None)
        return out

    def _root_sampling(self) -> Dict[str, Any]:
        s = self.raw_settings.get("sampling")
        return s if isinstance(s, dict) else {}

    @property
    def use_sampling(self) -> bool:
        s = self._root_sampling()
        return bool(s.get("use_sampling", False))

    @property
    def base_version(self) -> str:
        ps = self.price_simulator
        return str(ps.get("base_version") or ps.get("output_version") or "latest") or "latest"

    @property
    def start_date(self) -> str:
        s = self._root_sampling()
        return str(s.get("start_date", "") or "").strip()

    @property
    def end_date(self) -> str:
        s = self._root_sampling()
        return str(s.get("end_date", "") or "").strip()

    @property
    def max_workers(self) -> Union[Literal["auto"], int]:
        return SettingsBase.parse_max_workers(
            self.price_simulator.get("max_workers", "auto")
        )

    @property
    def fees(self) -> Dict[str, Any]:
        f = self.raw_settings.get("fees")
        return f if isinstance(f, dict) else {}


StrategyPriceFactorSimulationSettings = StrategyPriceSimulatorSettings

__all__ = [
    "StrategyPriceSimulatorSettings",
    "StrategyPriceFactorSimulationSettings",
]
