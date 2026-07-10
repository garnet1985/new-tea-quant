"""Simulation settings (``settings.simulation``)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.modules.strategy.core.engines.shared.data_class.investment import (
    DEFAULT_EXECUTE_STEPS,
    EXIT_TRIGGER_EXECUTE_STEPS,
    ExecuteStep,
)

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass
class SimulationSettings(SettingsBase):
    """``settings.simulation`` block."""

    raw_settings: Dict[str, Any]

    @property
    def simulation(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "simulation")

    @property
    def execute_steps(self) -> List[str]:
        raw = self.simulation.get("execute_steps")
        if not isinstance(raw, list):
            return [step.value for step in DEFAULT_EXECUTE_STEPS]
        return [str(item).strip() for item in raw if str(item).strip()]

    def apply_defaults(self) -> None:
        if "simulation" not in self.raw_settings or not isinstance(self.raw_settings["simulation"], dict):
            self.raw_settings["simulation"] = {}
        if "execute_steps" not in self.simulation:
            self.raw_settings["simulation"]["execute_steps"] = [
                step.value for step in DEFAULT_EXECUTE_STEPS
            ]

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        self.apply_defaults()

        simulation = self.simulation
        if not isinstance(self.raw_settings.get("simulation"), dict):
            SettingsBase.add_critical(
                report,
                "simulation",
                "simulation must be dict",
                suggested_fix="Set simulation to {}",
            )
            return report

        raw_steps = simulation.get("execute_steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            SettingsBase.add_critical(
                report,
                "simulation.execute_steps",
                "execute_steps must be a non-empty list",
                suggested_fix=f"Use default: {[s.value for s in DEFAULT_EXECUTE_STEPS]}",
            )
            return report

        parsed: List[ExecuteStep] = []
        seen: set[str] = set()
        for idx, item in enumerate(raw_steps):
            field_path = f"simulation.execute_steps[{idx}]"
            try:
                step = ExecuteStep.parse(item)
            except ValueError as exc:
                SettingsBase.add_critical(
                    report,
                    field_path,
                    str(exc),
                    suggested_fix=f"Allowed: {[s.value for s in ExecuteStep]}",
                )
                continue
            if step.value in seen:
                SettingsBase.add_critical(
                    report,
                    field_path,
                    f"duplicate execute step: {step.value!r}",
                    suggested_fix="Remove duplicate entries",
                )
                continue
            seen.add(step.value)
            parsed.append(step)

        if not report.is_valid:
            return report

        step_values = {step.value for step in parsed}
        if ExecuteStep.CHECK_SETTLEMENT.value not in step_values:
            SettingsBase.add_critical(
                report,
                "simulation.execute_steps",
                "missing required step check_settlement",
                suggested_fix="Include check_settlement (settlement gate before exit triggers)",
            )

        if not step_values.intersection({s.value for s in EXIT_TRIGGER_EXECUTE_STEPS}):
            SettingsBase.add_critical(
                report,
                "simulation.execute_steps",
                "must include at least one exit trigger step "
                "(check_stop_loss, check_take_profit, or check_expiration)",
                suggested_fix="Otherwise positions can only close via simulate_end",
            )

        return report

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return {
            "execute_steps": list(self.execute_steps),
        }


def resolve_execute_steps(settings: Dict[str, Any]) -> List[ExecuteStep]:
    """Parse ``simulation.execute_steps`` after defaults."""
    helper = SimulationSettings(raw_settings=settings)
    helper.apply_defaults()
    return [ExecuteStep.parse(item) for item in helper.execute_steps]


__all__ = ["SimulationSettings", "resolve_execute_steps"]
