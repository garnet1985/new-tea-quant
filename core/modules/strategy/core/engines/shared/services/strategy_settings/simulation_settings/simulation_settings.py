"""``settings.simulation`` 门面：execution / assumption / risk_control。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, TYPE_CHECKING

from core.modules.strategy.core.engines.shared.services.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.validation_report import (
    ValidationReport,
)

from .assumption import AssumptionSettings
from .execution import ExecutionSettings
from .risk_control import RiskControl
from .tradability import EdgesConfig, LiquidityConfig, TradabilityConfig

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.data_class.investment import ExecuteStep


@dataclass
class SimulationSettings(SettingsBase):
    """``settings.simulation`` — 组合 execution / assumption / risk_control。"""

    raw_settings: Dict[str, Any]
    execution: ExecutionSettings = field(init=False, repr=False)
    assumption: AssumptionSettings = field(init=False, repr=False)
    risk_control: RiskControl = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "execution", ExecutionSettings(raw_settings=self.raw_settings)
        )
        object.__setattr__(
            self, "assumption", AssumptionSettings(raw_settings=self.raw_settings)
        )
        object.__setattr__(
            self, "risk_control", RiskControl(raw_settings=self.raw_settings)
        )

    @property
    def simulation(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "simulation")

    @property
    def start_date(self) -> str:
        return self.execution.start_date

    @property
    def end_date(self) -> str:
        return self.execution.end_date

    @property
    def mode(self) -> str:
        return self.execution.mode

    @property
    def steps(self) -> List[str]:
        return self.execution.steps

    @property
    def tradability(self) -> TradabilityConfig:
        return self.assumption.tradability

    @property
    def edges(self) -> EdgesConfig:
        return self.tradability.edges

    @property
    def liquidity(self) -> LiquidityConfig:
        return self.tradability.liquidity

    @property
    def enter_price(self) -> str:
        return self.tradability.enter_price

    @property
    def exit_price(self) -> str:
        return self.tradability.exit_price

    @property
    def monitor_price(self) -> str:
        return self.tradability.monitor_price

    @property
    def delisted_exit_price(self) -> str:
        return self.tradability.delisted_exit_price

    @property
    def allow_enter_at_limit_up(self) -> bool:
        return self.edges.allow_enter_at_limit_up

    @property
    def allow_exit_at_limit_down(self) -> bool:
        return self.edges.allow_exit_at_limit_down

    def parsed_execute_steps(self) -> List["ExecuteStep"]:
        return self.execution.parsed_steps()

    def apply_defaults(self) -> None:
        if "simulation" not in self.raw_settings or not isinstance(
            self.raw_settings["simulation"], dict
        ):
            self.raw_settings["simulation"] = {}
        self.execution.apply_defaults()
        self.assumption.apply_defaults()
        self.risk_control.apply_defaults()

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        if not isinstance(self.raw_settings.get("simulation"), dict):
            SettingsBase.add_critical(
                report,
                "simulation",
                "simulation must be dict",
                suggested_fix="Set simulation to {}",
            )
            return report

        for part in (self.execution, self.assumption, self.risk_control):
            part_report = part.validate()
            report.errors.extend(part_report.errors)
            report.warnings.extend(part_report.warnings)
            if not part_report.is_valid:
                report.is_valid = False

        self._warn_legacy_sampling_dates(report)
        return report

    def _warn_legacy_sampling_dates(self, report: ValidationReport) -> None:
        sampling = SettingsBase.ensure_dict_block(self.raw_settings, "sampling")
        if not str(sampling.get("start_date") or "").strip() and not str(
            sampling.get("end_date") or ""
        ).strip():
            return
        SettingsBase.add_warning(
            report,
            "sampling.start_date/end_date",
            "dates under sampling are ignored; use simulation.execution.start_date/end_date",
            suggested_fix="Move start_date/end_date into settings.simulation.execution",
        )

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return {
            "execution": self.execution.to_dict(),
            "assumption": self.assumption.to_dict(),
            "risk_control": self.risk_control.to_dict(),
        }


__all__ = ["SimulationSettings"]
