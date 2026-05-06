#!/usr/bin/env python3
"""Capital simulator settings data classes."""

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
_VALID_MODES = frozenset({"equal_capital", "equal_shares", "kelly", "custom"})

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
        StrategySettings,
    )


@dataclass
class AllocationConfig:
    mode: str = "equal_capital"
    max_portfolio_size: int = 10
    max_weight_per_stock: float = 0.3
    lot_size: int = 100
    lots_per_trade: int = 1
    kelly_fraction: float = 0.5


@dataclass
class OutputConfig:
    save_trades: bool = True
    save_equity_curve: bool = True


@dataclass
class StrategyCapitalSimulatorSettings(SettingsBase):
    raw_settings: Dict[str, Any]
    _capital_simulator_validated: bool = field(default=False, repr=False)

    @property
    def capital_simulator(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "capital_simulator")

    @classmethod
    def from_strategy_root(cls, root: Dict[str, Any]) -> "StrategyCapitalSimulatorSettings":
        if not isinstance(root, dict):
            root = {}
        SettingsBase.ensure_dict_block(root, "capital_simulator")
        return cls(raw_settings=root)

    @classmethod
    def from_base_settings(cls, base_settings: StrategySettings) -> "StrategyCapitalSimulatorSettings":
        return cls.from_strategy_root(base_settings.raw_settings)

    def apply_defaults(self) -> None:
        c = self.capital_simulator
        c.setdefault("base_version", "latest")
        c.setdefault("initial_capital", 1_000_000)
        alloc = c.get("allocation")
        if not isinstance(alloc, dict):
            alloc = {}
            c["allocation"] = alloc
        alloc.setdefault("mode", "equal_capital")
        alloc.setdefault("max_portfolio_size", 10)
        alloc.setdefault("max_weight_per_stock", 0.3)
        alloc.setdefault("lot_size", 100)
        alloc.setdefault("lots_per_trade", 1)
        alloc.setdefault("kelly_fraction", 0.5)
        out = c.get("output")
        if not isinstance(out, dict):
            out = {}
            c["output"] = out
        out.setdefault("save_trades", True)
        out.setdefault("save_equity_curve", True)

    def validate(self) -> ValidationReport:
        result = SettingsBase.new_validation()
        self.apply_defaults()

        alloc = self._parse_allocation()
        try:
            ic = float(self.capital_simulator.get("initial_capital", 1_000_000))
        except (TypeError, ValueError):
            ic = 0.0
        self.capital_simulator["initial_capital"] = max(ic, 0.0)
        if self.capital_simulator["initial_capital"] < 1000:
            SettingsBase.add_critical(result, "capital_simulator.initial_capital", "initial_capital 必须 >= 1000")
        if alloc.mode not in _VALID_MODES:
            SettingsBase.add_critical(result, "capital_simulator.allocation.mode", f"allocation.mode 无效: {alloc.mode}")
        if alloc.max_portfolio_size <= 0:
            SettingsBase.add_critical(result, "capital_simulator.allocation.max_portfolio_size", "max_portfolio_size 必须 > 0")
        bv = str(self.capital_simulator.get("base_version") or "latest")
        if bv != "latest":
            SettingsBase.add_warning(result, "capital_simulator.base_version", f"指定 base_version={bv}")
        self._validate_max_workers(result)
        SettingsBase.log_warnings(result, logger)
        self._capital_simulator_validated = True
        return result

    def _validate_max_workers(self, result: ValidationReport) -> None:
        SettingsBase.validate_max_workers_field(
            report=result,
            container=self.capital_simulator,
            key="max_workers",
            field_path="capital_simulator.max_workers",
            invalid_message='capital_simulator.max_workers 须为 "auto" 或正整数',
        )

    def _parse_allocation(self) -> AllocationConfig:
        a = self.capital_simulator.get("allocation") or {}
        if not isinstance(a, dict):
            a = {}
            self.capital_simulator["allocation"] = a
        try:
            mps = max(int(a.get("max_portfolio_size", 10)), 1)
        except (TypeError, ValueError):
            mps = 10
        try:
            mw = max(min(float(a.get("max_weight_per_stock", 0.3)), 1.0), 0.0)
        except (TypeError, ValueError):
            mw = 0.3
        try:
            lot = max(int(a.get("lot_size", 100)), 1)
        except (TypeError, ValueError):
            lot = 100
        try:
            lots = max(int(a.get("lots_per_trade", 1)), 1)
        except (TypeError, ValueError):
            lots = 1
        try:
            kf = max(min(float(a.get("kelly_fraction", 0.5)), 1.0), 0.0)
        except (TypeError, ValueError):
            kf = 0.5
        mode = str(a.get("mode", "equal_capital") or "equal_capital")
        return AllocationConfig(mode=mode, max_portfolio_size=mps, max_weight_per_stock=mw, lot_size=lot, lots_per_trade=lots, kelly_fraction=kf)

    def _parse_output(self) -> OutputConfig:
        o = self.capital_simulator.get("output") or {}
        if not isinstance(o, dict):
            o = {}
            self.capital_simulator["output"] = o
        return OutputConfig(
            save_trades=bool(o.get("save_trades", True)),
            save_equity_curve=bool(o.get("save_equity_curve", True)),
        )

    def get_fees_config_with_priority(self) -> Dict[str, Any]:
        top = self.raw_settings.get("fees", {}) or {}
        return top if isinstance(top, dict) else {}

    def to_dict(self) -> Dict[str, Any]:
        out = self.deep_copy_dict(dict(self.capital_simulator))
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
        return str(self.capital_simulator.get("base_version", "latest") or "latest")

    @property
    def initial_capital(self) -> float:
        try:
            return float(self.capital_simulator.get("initial_capital", 1_000_000))
        except (TypeError, ValueError):
            return 1_000_000.0

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
            self.capital_simulator.get("max_workers", "auto")
        )

    @property
    def allocation(self) -> AllocationConfig:
        return self._parse_allocation()

    @property
    def output(self) -> OutputConfig:
        return self._parse_output()


CapitalAllocationSettings = StrategyCapitalSimulatorSettings

__all__ = [
    "_VALID_MODES",
    "AllocationConfig",
    "OutputConfig",
    "StrategyCapitalSimulatorSettings",
    "CapitalAllocationSettings",
]
