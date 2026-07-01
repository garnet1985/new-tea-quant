"""slice_based 模式 runtime context。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Dict, List

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.strategy.core.engines.enumerator.shared.runtime import RuntimeContext


@dataclass
class SliceBasedRuntimeContext(RuntimeContext):
    """slice_based 模式专用 RuntimeContext。"""

    EXECUTION_MODE: ClassVar[BacktestMode] = BacktestMode.SLICE_BASED

    @staticmethod
    def calendar_from_job(job: Dict[str, Any]) -> Dict[str, Any]:
        calendar = job.get("backtest_calendar")
        if not isinstance(calendar, dict):
            raise ValueError("slice_based job 缺少 backtest_calendar")
        return dict(calendar)

    @classmethod
    def open_dates_from_job(cls, job: Dict[str, Any]) -> List[str]:
        calendar = cls.calendar_from_job(job)
        open_dates = calendar.get("open_dates")
        if not isinstance(open_dates, list) or not open_dates:
            raise ValueError("backtest_calendar.open_dates 须为非空 list")
        return list(open_dates)

    @classmethod
    def assert_mode(cls, context: RuntimeContext) -> None:
        mode = BacktestMode.normalize(context.execution_mode)
        if mode != cls.EXECUTION_MODE.value:
            raise ValueError(
                f"期望 execution_mode={cls.EXECUTION_MODE.value!r}, "
                f"实际 {mode!r}"
            )


__all__ = ["SliceBasedRuntimeContext"]
