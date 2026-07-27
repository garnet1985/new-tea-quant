"""``settings.calculation`` — update_mode / recompute / execution。

消费者: TagSettings

``calculation`` ≈ strategy.simulation（块名保留）；
``calculation.execution`` 与 ``simulation.execution`` 同构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.tag.core.enums import TagExecutionMode, TagUpdateMode

from .settings_base import SettingsBase
from .validation_report import ValidationReport

_KNOWN_MODES = frozenset(
    {TagExecutionMode.ENTITY_BASED.value, TagExecutionMode.SLICE_BASED.value}
)
_KNOWN_UPDATE_MODES = frozenset(
    {TagUpdateMode.INCREMENTAL.value, TagUpdateMode.REFRESH.value}
)


@dataclass(frozen=True)
class CalculationPeriod:
    """已 resolve 的计算开市日区间（空值已用系统默认补齐）。"""

    start_date: str
    end_date: str

    def to_dict(self) -> Dict[str, Any]:
        return {"start_date": self.start_date, "end_date": self.end_date}

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "CalculationPeriod":
        data = raw or {}
        return cls(
            start_date=str(data.get("start_date") or ""),
            end_date=str(data.get("end_date") or ""),
        )


@dataclass
class ExecutionSettings(SettingsBase):
    """``settings.calculation.execution``（日历窗 + entity/slice mode）。"""

    raw_settings: Dict[str, Any]

    @property
    def calculation(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "calculation")

    @property
    def execution(self) -> Dict[str, Any]:
        block = self.calculation.get("execution")
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
        calc = self.raw_settings.setdefault("calculation", {})
        if not isinstance(calc, dict):
            self.raw_settings["calculation"] = {}
            calc = self.raw_settings["calculation"]
        execution = calc.setdefault("execution", {})
        if not isinstance(execution, dict):
            calc["execution"] = {}
            execution = calc["execution"]
        execution.setdefault("start_date", "")
        execution.setdefault("end_date", "")
        execution.setdefault("mode", TagExecutionMode.ENTITY_BASED.value)

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        calc = self.raw_settings.get("calculation")
        if calc is not None and not isinstance(calc, dict):
            SettingsBase.add_critical(report, "calculation", "calculation must be dict")
            return report

        execution_raw = self.calculation.get("execution")
        if execution_raw is not None and not isinstance(execution_raw, dict):
            SettingsBase.add_critical(
                report,
                "calculation.execution",
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
                "calculation.execution.start_date",
                f"invalid date {start!r}, expected YYYYMMDD",
                suggested_fix='Use e.g. "20240101", or "" for system default',
            )
        if end and not self._is_yyyymmdd(end):
            SettingsBase.add_critical(
                report,
                "calculation.execution.end_date",
                f"invalid date {end!r}, expected YYYYMMDD",
                suggested_fix='Use e.g. "20241231", or "" for system default',
            )
        if start and end and self._is_yyyymmdd(start) and self._is_yyyymmdd(end):
            if start > end:
                SettingsBase.add_critical(
                    report,
                    "calculation.execution.start_date",
                    f"start_date {start} > end_date {end}",
                    suggested_fix="Ensure start_date <= end_date",
                )

    def _validate_mode(self, report: ValidationReport) -> None:
        mode = self.mode
        if not mode:
            SettingsBase.add_critical(
                report,
                "calculation.execution.mode",
                "mode is required",
                suggested_fix=f"Use one of {sorted(_KNOWN_MODES)}",
            )
            return
        if mode not in _KNOWN_MODES:
            SettingsBase.add_critical(
                report,
                "calculation.execution.mode",
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

    def resolve_period(self) -> CalculationPeriod:
        """把 execution.start/end 空值补成系统默认。"""
        from core.infra.project_context import ProjectContext
        from core.utils.date.date_utils import DateUtils

        start_date = self.start_date
        end_date = self.end_date
        if not start_date:
            start_date = ProjectContext.config.get_default_start_date()
        if not end_date:
            try:
                end_date = DateUtils.today()
            except Exception:
                end_date = ""
        return CalculationPeriod(start_date=start_date, end_date=end_date)

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "mode": self.mode or TagExecutionMode.ENTITY_BASED.value,
        }


@dataclass
class CalculationSettings(SettingsBase):
    """``settings.calculation`` — update_mode / recompute / execution。"""

    raw_settings: Dict[str, Any]
    execution: ExecutionSettings = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "execution", ExecutionSettings(raw_settings=self.raw_settings)
        )

    @property
    def calculation(self) -> Dict[str, Any]:
        return SettingsBase.ensure_dict_block(self.raw_settings, "calculation")

    @property
    def update_mode(self) -> str:
        return str(self.calculation.get("update_mode") or "").strip().lower()

    @property
    def recompute(self) -> bool:
        return bool(self.calculation.get("recompute", False))

    @property
    def start_date(self) -> str:
        return self.execution.start_date

    @property
    def end_date(self) -> str:
        return self.execution.end_date

    @property
    def mode(self) -> str:
        return self.execution.mode

    def effective_update_mode(self) -> str:
        """recompute=True 时强制 refresh。"""
        if self.recompute:
            return TagUpdateMode.REFRESH.value
        return self.update_mode or TagUpdateMode.INCREMENTAL.value

    def resolve_period(self) -> CalculationPeriod:
        return self.execution.resolve_period()

    def apply_defaults(self) -> None:
        if "calculation" not in self.raw_settings or not isinstance(
            self.raw_settings["calculation"], dict
        ):
            self.raw_settings["calculation"] = {}
        calc = self.raw_settings["calculation"]
        calc.setdefault("update_mode", TagUpdateMode.INCREMENTAL.value)
        calc.setdefault("recompute", False)
        self.execution.apply_defaults()

    def validate(self) -> ValidationReport:
        report = SettingsBase.new_validation()
        calc = self.raw_settings.get("calculation")
        if calc is not None and not isinstance(calc, dict):
            SettingsBase.add_critical(report, "calculation", "calculation must be dict")
            return report

        self.apply_defaults()

        update_mode = self.update_mode
        if update_mode not in _KNOWN_UPDATE_MODES:
            SettingsBase.add_critical(
                report,
                "calculation.update_mode",
                f"invalid update_mode {update_mode!r}",
                suggested_fix=f"Use one of {sorted(_KNOWN_UPDATE_MODES)}",
            )

        exec_report = self.execution.validate()
        report.errors.extend(exec_report.errors)
        report.warnings.extend(exec_report.warnings)
        if not exec_report.is_valid:
            report.is_valid = False

        mode = self.mode
        if mode == TagExecutionMode.SLICE_BASED.value:
            if not self.recompute and self.update_mode != TagUpdateMode.REFRESH.value:
                SettingsBase.add_critical(
                    report,
                    "calculation",
                    "slice_based currently requires recompute=true or update_mode=refresh",
                )

        return report

    def normalized_mode(self) -> str:
        return BacktestMode.normalize(self.mode or TagExecutionMode.ENTITY_BASED.value)

    def to_dict(self) -> Dict[str, Any]:
        self.apply_defaults()
        return {
            "update_mode": self.update_mode or TagUpdateMode.INCREMENTAL.value,
            "recompute": self.recompute,
            "execution": self.execution.to_dict(),
        }


__all__ = ["CalculationPeriod", "ExecutionSettings", "CalculationSettings"]
