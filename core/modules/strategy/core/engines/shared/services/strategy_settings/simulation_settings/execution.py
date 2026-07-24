"""``simulation.execution`` — 时间窗 + mode + Investment steps。"""

from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict, List, TYPE_CHECKING

from core.modules.strategy.core.engines.shared.services.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.validation_report import (
    ValidationReport,
)

if TYPE_CHECKING:
    from core.modules.strategy.core.engines.shared.data_class.investments import ExecuteStep

_KNOWN_MODES = frozenset({"entity_based", "slice_based"})
_DEFAULT_STEPS = [
    "check_settlement",
    "check_stop_loss",
    "check_take_profit",
    "check_expiration",
]
_EXIT_TRIGGER_STEPS = frozenset(
    {"check_stop_loss", "check_take_profit", "check_expiration"}
)


@dataclass
class ExecutionSettings(SettingsBase):
    """``settings.simulation.execution``。"""

    raw_settings: Dict[str, Any]

    @property
    def simulation(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "simulation")

    @property
    def execution(self) -> Dict[str, Any]:
        block = self.simulation.get("execution")
        return block if isinstance(block, dict) else {}

    @property
    def start_date(self) -> str:
        return str(self.execution.get("start_date") or "").strip()

    @property
    def end_date(self) -> str:
        return str(self.execution.get("end_date") or "").strip()

    @property
    def mode(self) -> str:
        return str(self.execution.get("mode") or "").strip().lower()

    @property
    def steps(self) -> List[str]:
        raw = self.execution.get("steps")
        if not isinstance(raw, list):
            return list(_DEFAULT_STEPS)
        return [str(item).strip() for item in raw if str(item).strip()]

    def parsed_steps(self) -> List["ExecuteStep"]:
        from core.modules.strategy.core.engines.shared.data_class.investments import (
            ExecuteStep,
        )

        self.apply_defaults()
        return [ExecuteStep.parse(item) for item in self.steps]

    def apply_defaults(self) -> None:
        sim = self.raw_settings.setdefault("simulation", {})
        if not isinstance(sim, dict):
            self.raw_settings["simulation"] = {}
            sim = self.raw_settings["simulation"]
        execution = sim.setdefault("execution", {})
        if not isinstance(execution, dict):
            sim["execution"] = {}
            execution = sim["execution"]
        execution.setdefault("start_date", "")
        execution.setdefault("end_date", "")
        execution.setdefault("mode", "entity_based")
        execution.setdefault("steps", list(_DEFAULT_STEPS))

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        sim = self.raw_settings.get("simulation")
        if sim is not None and not isinstance(sim, dict):
            SettingsBase.add_critical(
                report, "simulation", "simulation must be dict"
            )
            return report

        execution_raw = self.simulation.get("execution")
        if execution_raw is not None and not isinstance(execution_raw, dict):
            SettingsBase.add_critical(
                report,
                "simulation.execution",
                "execution must be dict",
            )
            return report

        self.apply_defaults()
        self._validate_period(report)
        self._validate_mode(report)
        self._validate_steps(report)
        return report

    def _validate_period(self, report: ValidationReport) -> None:
        start = self.start_date
        end = self.end_date
        if start and not self._is_yyyymmdd(start):
            SettingsBase.add_critical(
                report,
                "simulation.execution.start_date",
                f"invalid date {start!r}, expected YYYYMMDD",
                suggested_fix='Use e.g. "20240101", or "" for system default',
            )
        if end and not self._is_yyyymmdd(end):
            SettingsBase.add_critical(
                report,
                "simulation.execution.end_date",
                f"invalid date {end!r}, expected YYYYMMDD",
                suggested_fix='Use e.g. "20241231", or "" for system default',
            )
        if start and end and self._is_yyyymmdd(start) and self._is_yyyymmdd(end):
            if start > end:
                SettingsBase.add_critical(
                    report,
                    "simulation.execution.start_date",
                    f"start_date {start} > end_date {end}",
                    suggested_fix="Ensure start_date <= end_date",
                )

    def _validate_mode(self, report: ValidationReport) -> None:
        mode = self.mode
        if not mode:
            SettingsBase.add_critical(
                report,
                "simulation.execution.mode",
                "mode is required",
                suggested_fix=f"Use one of {sorted(_KNOWN_MODES)}",
            )
            return
        if mode not in _KNOWN_MODES:
            SettingsBase.add_critical(
                report,
                "simulation.execution.mode",
                f"invalid mode {mode!r}",
                suggested_fix=f"Use one of {sorted(_KNOWN_MODES)}",
            )

    def _validate_steps(self, report: ValidationReport) -> None:
        from core.modules.strategy.core.engines.shared.data_class.investments import (
            ExecuteStep,
        )

        raw_steps = self.execution.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            SettingsBase.add_critical(
                report,
                "simulation.execution.steps",
                "steps must be a non-empty list",
                suggested_fix=f"Use default: {_DEFAULT_STEPS}",
            )
            return

        parsed: List[ExecuteStep] = []
        seen: set[str] = set()
        for idx, item in enumerate(raw_steps):
            field_path = f"simulation.execution.steps[{idx}]"
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
                )
                continue
            seen.add(step.value)
            parsed.append(step)

        if not report.is_valid:
            return

        step_values = {step.value for step in parsed}
        if ExecuteStep.CHECK_SETTLEMENT.value not in step_values:
            SettingsBase.add_critical(
                report,
                "simulation.execution.steps",
                "missing required step check_settlement",
            )
        if not step_values.intersection(_EXIT_TRIGGER_STEPS):
            SettingsBase.add_critical(
                report,
                "simulation.execution.steps",
                "must include at least one exit trigger step "
                "(check_stop_loss, check_take_profit, or check_expiration)",
            )

    @staticmethod
    def _is_yyyymmdd(value: str) -> bool:
        if len(value) != 8 or not value.isdigit():
            return False
        try:
            datetime.strptime(value, "%Y%m%d")
        except ValueError:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "mode": self.mode or "entity_based",
            "steps": list(self.steps),
        }


__all__ = ["ExecutionSettings"]
