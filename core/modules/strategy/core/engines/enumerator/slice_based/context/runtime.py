"""slice_based 运行配置 context。"""
from __future__ import annotations

from typing import Any, Dict, List

from core.modules.strategy.core.engines.enumerator.shared.runtime import RuntimeContext


class SliceRuntimeContext:
    """slice_based 模式 runtime 视图。"""

    EXECUTION_MODE = "slice_based"

    @staticmethod
    def calendar_from_job(job: Dict[str, Any]) -> Dict[str, Any]:
        calendar = job.get("backtest_calendar")
        if isinstance(calendar, dict):
            return dict(calendar)
        open_dates = list(job.get("open_dates") or [])
        return {
            "open_dates": open_dates,
            "period_start": job.get("start_date"),
            "period_end": job.get("end_date"),
        }

    @staticmethod
    def open_dates_from_job(job: Dict[str, Any]) -> List[str]:
        calendar = SliceRuntimeContext.calendar_from_job(job)
        return list(calendar.get("open_dates") or job.get("open_dates") or [])

    @staticmethod
    def assert_mode(context: RuntimeContext) -> None:
        if context.execution_mode != SliceRuntimeContext.EXECUTION_MODE:
            raise ValueError(
                f"期望 execution_mode={SliceRuntimeContext.EXECUTION_MODE!r}, "
                f"实际 {context.execution_mode!r}"
            )


__all__ = ["SliceRuntimeContext"]
