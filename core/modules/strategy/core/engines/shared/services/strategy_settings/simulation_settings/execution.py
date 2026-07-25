"""``simulation.execution`` — 时间窗 + mode。"""

from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from typing import Any, Dict

from core.modules.strategy.core.engines.shared.services.strategy_settings.settings_base import (
    SettingsBase,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.validation_report import (
    ValidationReport,
)

_KNOWN_MODES = frozenset({"entity_based", "slice_based"})



@dataclass(frozen=True)
class BacktestPeriod:
    """已 resolve 的回测开市日区间（settings 空值已用系统默认补齐）。"""

    start_date: str
    end_date: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
        }

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "BacktestPeriod":
        data = raw or {}
        return cls(
            start_date=str(data.get("start_date") or ""),
            end_date=str(data.get("end_date") or ""),
        )


@dataclass
class ExecutionSettings(SettingsBase):
    """``settings.simulation.execution``（日历窗 + entity/slice mode）。"""

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
        # 历史误放的 steps 不再使用；避免残留误导
        execution.pop("steps", None)

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

    @staticmethod
    def _is_yyyymmdd(value: str) -> bool:
        if len(value) != 8 or not value.isdigit():
            return False
        try:
            datetime.strptime(value, "%Y%m%d")
        except ValueError:
            return False
        return True


    def resolve_period(self) -> BacktestPeriod:
        """把 execution.start/end 空值补成系统默认（回测前统一入口）。"""
        from core.infra.project_context import ProjectContext
        from core.modules.strategy.core.services.entity_loader.global_entity_loader import (
            GlobalEntityCache,
        )

        start_date = self.start_date
        end_date = self.end_date
        if not end_date:
            end_date = GlobalEntityCache.load_latest_completed_trading_date()
        if not start_date:
            start_date = ProjectContext.config.get_default_start_date()
        return BacktestPeriod(start_date=start_date, end_date=end_date)

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "mode": self.mode or "entity_based",
        }


__all__ = ["BacktestPeriod", "ExecutionSettings"]
