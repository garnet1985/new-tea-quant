"""Simulation settings (``settings.simulation``)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from core.modules.strategy.core.engines.shared.data_class.investment import (
    DEFAULT_EXECUTE_STEPS,
    EXIT_TRIGGER_EXECUTE_STEPS,
    ExecuteStep,
)

from .settings_base import SettingsBase
from .validation_report import ValidationReport


@dataclass(frozen=True)
class SimulationEdgesConfig:
    """``settings.simulation.edges`` — 成交边角假设（risk / simulation policy）。

    贴涨/跌停是否允许成交是仿真假设，不是市场硬规则。
    """

    allow_buy_at_limit_up: bool = False
    allow_sell_at_limit_down: bool = False


@dataclass
class SimulationSettings(SettingsBase):
    """``settings.simulation`` block（时间窗 + 成交假设）。"""

    raw_settings: Dict[str, Any]

    @property
    def simulation(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "simulation")

    @property
    def start_date(self) -> str:
        """已配置的回测开始日（YYYYMMDD）；空表示交由系统默认。"""
        return str(self.simulation.get("start_date") or "").strip()

    @property
    def end_date(self) -> str:
        """已配置的回测结束日（YYYYMMDD）；空表示交由系统默认。"""
        return str(self.simulation.get("end_date") or "").strip()

    @property
    def execute_steps(self) -> List[str]:
        raw = self.simulation.get("execute_steps")
        if not isinstance(raw, list):
            return [step.value for step in DEFAULT_EXECUTE_STEPS]
        return [str(item).strip() for item in raw if str(item).strip()]

    @property
    def edges(self) -> SimulationEdgesConfig:
        return self._parse_edges()

    @property
    def allow_buy_at_limit_up(self) -> bool:
        """贴涨停时是否仍允许买入成交（默认 False）。"""
        return self.edges.allow_buy_at_limit_up

    @property
    def allow_sell_at_limit_down(self) -> bool:
        """贴跌停时是否仍允许卖出成交（默认 False）。"""
        return self.edges.allow_sell_at_limit_down

    def apply_defaults(self) -> None:
        if "simulation" not in self.raw_settings or not isinstance(
            self.raw_settings["simulation"], dict
        ):
            self.raw_settings["simulation"] = {}
        sim = self.raw_settings["simulation"]
        if "start_date" not in sim:
            sim["start_date"] = ""
        if "end_date" not in sim:
            sim["end_date"] = ""
        if "execute_steps" not in sim:
            sim["execute_steps"] = [step.value for step in DEFAULT_EXECUTE_STEPS]
        if "edges" not in sim:
            sim["edges"] = {}
        edges = sim.get("edges")
        if isinstance(edges, dict):
            edges.setdefault("allow_buy_at_limit_up", False)
            edges.setdefault("allow_sell_at_limit_down", False)

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

        # edges 类型须在 apply_defaults 改写前检查
        edges_raw = self.simulation.get("edges")
        if edges_raw is not None and not isinstance(edges_raw, dict):
            SettingsBase.add_critical(
                report,
                "simulation.edges",
                "edges must be dict",
                suggested_fix=(
                    'Use {"allow_buy_at_limit_up": false, '
                    '"allow_sell_at_limit_down": false}'
                ),
            )

        self.apply_defaults()
        self._validate_period(report)
        self._warn_legacy_sampling_dates(report)
        self._validate_execute_steps(report)
        return report

    def _validate_period(self, report: ValidationReport) -> None:
        start = self.start_date
        end = self.end_date
        if start:
            if not self._is_yyyymmdd(start):
                SettingsBase.add_critical(
                    report,
                    "simulation.start_date",
                    f"invalid date {start!r}, expected YYYYMMDD",
                    suggested_fix='Use e.g. "20240101", or "" for system default',
                )
        if end:
            if not self._is_yyyymmdd(end):
                SettingsBase.add_critical(
                    report,
                    "simulation.end_date",
                    f"invalid date {end!r}, expected YYYYMMDD",
                    suggested_fix='Use e.g. "20241231", or "" for system default',
                )
        if start and end and self._is_yyyymmdd(start) and self._is_yyyymmdd(end):
            if start > end:
                SettingsBase.add_critical(
                    report,
                    "simulation.start_date",
                    f"start_date {start} > end_date {end}",
                    suggested_fix="Ensure start_date <= end_date",
                )

    def _warn_legacy_sampling_dates(self, report: ValidationReport) -> None:
        sampling = SettingsBase.ensure_dict_block(self.raw_settings, "sampling")
        legacy_start = str(sampling.get("start_date") or "").strip()
        legacy_end = str(sampling.get("end_date") or "").strip()
        if not legacy_start and not legacy_end:
            return
        SettingsBase.add_warning(
            report,
            "sampling.start_date/end_date",
            "dates under sampling are ignored; use simulation.start_date/end_date",
            suggested_fix="Move start_date/end_date into settings.simulation",
        )

    def _validate_execute_steps(self, report: ValidationReport) -> None:
        simulation = self.simulation
        raw_steps = simulation.get("execute_steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            SettingsBase.add_critical(
                report,
                "simulation.execute_steps",
                "execute_steps must be a non-empty list",
                suggested_fix=f"Use default: {[s.value for s in DEFAULT_EXECUTE_STEPS]}",
            )
            return

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
            return

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

    def _parse_edges(self) -> SimulationEdgesConfig:
        raw = self.simulation.get("edges")
        if not isinstance(raw, dict):
            raw = {}
        return SimulationEdgesConfig(
            allow_buy_at_limit_up=bool(raw.get("allow_buy_at_limit_up", False)),
            allow_sell_at_limit_down=bool(raw.get("allow_sell_at_limit_down", False)),
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
        edges = self.edges
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "execute_steps": list(self.execute_steps),
            "edges": {
                "allow_buy_at_limit_up": edges.allow_buy_at_limit_up,
                "allow_sell_at_limit_down": edges.allow_sell_at_limit_down,
            },
        }

    def parsed_execute_steps(self) -> List[ExecuteStep]:
        """Parse ``simulation.execute_steps`` after defaults."""
        self.apply_defaults()
        return [ExecuteStep.parse(item) for item in self.execute_steps]


__all__ = [
    "SimulationEdgesConfig",
    "SimulationSettings",
]
