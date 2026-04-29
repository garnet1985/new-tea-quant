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
    _missing_use_sampling_at_load: bool = field(default=False, repr=False)
    _price_simulator_validated: bool = field(default=False, repr=False)

    @property
    def price_simulator(self) -> Dict[str, Any]:
        block = self.raw_settings.get("price_simulator")
        if not isinstance(block, dict):
            block = {}
            self.raw_settings["price_simulator"] = block
        return block

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> "StrategyPriceSimulatorSettings":
        if not isinstance(root, dict):
            root = {}
        block = root.get("price_simulator")
        missing_us = not isinstance(block, dict) or "use_sampling" not in block
        if not isinstance(block, dict):
            block = {}
            root["price_simulator"] = block
        return cls(raw_settings=root, _missing_use_sampling_at_load=missing_us)

    @classmethod
    def from_base_settings(cls, base_settings: StrategySettings) -> "StrategyPriceSimulatorSettings":
        return cls.from_strategy_root(base_settings.raw_settings)

    def apply_defaults(self) -> None:
        ps = self.price_simulator
        ps.setdefault("use_sampling", False)
        if "base_version" not in ps and "output_version" in ps:
            ps["base_version"] = ps.get("output_version") or "latest"
        ps.setdefault("base_version", "latest")
        ps.setdefault("max_workers", "auto")
        ps.setdefault("start_date", "")
        ps.setdefault("end_date", "")

    def validate(self) -> ValidationReport:
        result = SettingsBase.new_validation()
        self.apply_defaults()
        bv = str(self.price_simulator.get("base_version") or "latest")
        if bv != "latest":
            SettingsBase.add_warning(result, "price_simulator.base_version", f"指定 base_version={bv}")
        if self._missing_use_sampling_at_load:
            SettingsBase.add_warning(result, "price_simulator.use_sampling", "use_sampling 未配置，默认 False")
        self._validate_max_workers(result)
        self._validate_fees_if_present(result)
        SettingsBase.log_warnings(result, logger)
        self._price_simulator_validated = True
        return result

    def _validate_max_workers(self, result: ValidationReport) -> None:
        ps = self.price_simulator
        mw = ps.get("max_workers", "auto")
        if mw == "auto" or mw is None:
            ps["max_workers"] = "auto"
            return
        try:
            ps["max_workers"] = max(int(mw), 1)
        except (TypeError, ValueError):
            SettingsBase.add_critical(
                result,
                "price_simulator.max_workers",
                'price_simulator.max_workers 须为 "auto" 或正整数',
            )

    def _validate_fees_if_present(self, result: ValidationReport) -> None:
        fees = self.price_simulator.get("fees")
        if fees is None:
            return
        if not isinstance(fees, dict):
            SettingsBase.add_critical(result, "price_simulator.fees", "fees 必须为对象（dict）")
            return
        required = ("commission_rate", "min_commission", "stamp_duty_rate", "transfer_fee_rate")
        for k in required:
            if k not in fees:
                SettingsBase.add_warning(result, f"price_simulator.fees.{k}", f"fees 缺少 {k}")

    def to_dict(self) -> Dict[str, Any]:
        return self.deep_copy_dict(dict(self.price_simulator))

    @property
    def use_sampling(self) -> bool:
        return bool(self.price_simulator.get("use_sampling", False))

    @property
    def base_version(self) -> str:
        ps = self.price_simulator
        return str(ps.get("base_version") or ps.get("output_version") or "latest") or "latest"

    @property
    def start_date(self) -> str:
        return str(self.price_simulator.get("start_date", "") or "")

    @property
    def end_date(self) -> str:
        return str(self.price_simulator.get("end_date", "") or "")

    @property
    def max_workers(self) -> Union[Literal["auto"], int]:
        mw = self.price_simulator.get("max_workers", "auto")
        if mw == "auto" or mw is None:
            return "auto"
        try:
            return max(int(mw), 1)
        except (TypeError, ValueError):
            return "auto"

    @property
    def fees(self) -> Dict[str, Any]:
        f = self.price_simulator.get("fees")
        return f if isinstance(f, dict) else {}


StrategyPriceFactorSimulationSettings = StrategyPriceSimulatorSettings

__all__ = [
    "StrategyPriceSimulatorSettings",
    "StrategyPriceFactorSimulationSettings",
]
