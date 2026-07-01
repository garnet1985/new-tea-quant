"""slice_based 枚举 worker：BacktestEngine execute_fn 入口。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.contracts import JobContext

from .compute import SliceBasedCompute

logger = logging.getLogger(__name__)


class SliceBasedWorker:
    """BacktestEngine 调用的 execute_fn：只做 payload 解析 + 策略计算。"""

    @classmethod
    def run(cls, context: JobContext) -> Dict[str, Any]:
        payload = cls.build_payload(dict(context.payload or {}))
        try:
            return SliceBasedCompute(payload).run()
        except Exception as exc:
            logger.error("slice_based enumeration failed: %s", exc, exc_info=True)
            return {
                "success": False,
                "bulk": True,
                "stock_results": [],
                "stock_ids": list(payload["stock_ids"]),
                "error": str(exc),
            }

    @classmethod
    def build_payload(
        cls,
        job: Dict[str, Any],
        global_data: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    ) -> Dict[str, Any]:
        if global_data is not None:
            job = {**job, "global_data": global_data}

        required = (
            "job_id",
            "strategy_name",
            "settings",
            "start_date",
            "end_date",
            "output_dir",
            "stock_ids",
            "backtest_calendar",
            "global_data",
            "worker_module_path",
            "worker_class_name",
            "enumeration_execution_mode",
        )
        for key in required:
            if key not in job:
                raise ValueError(f"slice_based job 缺少字段: {key}")

        global_data = job["global_data"]
        if not isinstance(global_data, dict):
            raise ValueError("slice_based job.global_data 须为 dict")

        stock_ids = job["stock_ids"]
        if not isinstance(stock_ids, list) or not stock_ids:
            raise ValueError("slice_based job.stock_ids 须为非空 list")

        calendar = job["backtest_calendar"]
        if not isinstance(calendar, dict) or not isinstance(calendar.get("open_dates"), list):
            raise ValueError("slice_based job.backtest_calendar.open_dates 须为 list")

        payload: Dict[str, Any] = {
            "job_id": str(job["job_id"]),
            "strategy_name": job["strategy_name"],
            "settings": job["settings"],
            "start_date": job["start_date"],
            "end_date": job["end_date"],
            "output_dir": job["output_dir"],
            "global_data": global_data,
            "stock_ids": list(stock_ids),
            "backtest_calendar": dict(calendar),
            "worker_module_path": job["worker_module_path"],
            "worker_class_name": job["worker_class_name"],
            "worker_file_path": str(job.get("worker_file_path") or ""),
            "enumeration_execution_mode": job["enumeration_execution_mode"],
        }
        if "slice_open_days" in job:
            payload["slice_open_days"] = job["slice_open_days"]
        for key, value in job.items():
            if str(key).startswith("_"):
                payload[key] = value
        return payload


__all__ = ["SliceBasedWorker"]
