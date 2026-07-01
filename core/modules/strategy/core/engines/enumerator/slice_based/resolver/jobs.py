"""slice_based job 构建。"""
from __future__ import annotations

from typing import Any, Dict, List

from .calendar import BacktestCalendarResolver


class SliceBasedJobs:
    """slice_based 调度输入（单 bulk job）。"""

    EXECUTION_MODE = "slice_based"

    @classmethod
    def build(
        cls,
        *,
        strategy_name: str,
        settings_payload: Dict[str, Any],
        output_dir: str,
        worker_ref: Dict[str, str],
        entity_ids: List[str],
        start_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        stock_ids = [str(x).strip() for x in entity_ids if str(x).strip()]
        if not stock_ids:
            raise ValueError("slice_based 需要非空 entity_ids")

        open_dates, calendar_dict = BacktestCalendarResolver.resolve(
            settings=settings_payload,
            start_date=start_date,
            end_date=end_date,
        )

        job_id = f"slice_based:{strategy_name}"
        return [
            {
                "job_id": job_id,
                "strategy_name": strategy_name,
                "settings": settings_payload,
                "start_date": start_date,
                "end_date": end_date,
                "output_dir": output_dir,
                "stock_ids": list(stock_ids),
                "open_dates": list(open_dates),
                "backtest_calendar": calendar_dict,
                "slice_open_days": "auto",
                "worker_module_path": worker_ref["worker_module_path"],
                "worker_class_name": worker_ref["worker_class_name"],
                "worker_file_path": str(worker_ref.get("worker_file_path") or ""),
                "enumeration_execution_mode": cls.EXECUTION_MODE,
            }
        ]


__all__ = ["SliceBasedJobs"]
