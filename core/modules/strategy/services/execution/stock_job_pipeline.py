"""Strategy BacktestEngine 执行结果与进度辅助（enum / price / scanner 共用）。"""
from __future__ import annotations

from typing import Any, Dict

from core.modules.backtest_engine.core.shared.types import (
    JobContext,
    JobReport,
    JobResult,
    JobStatus,
)


def job_report_to_job_result(report: JobReport) -> JobResult:
    data = report.data
    if (
        isinstance(data, dict)
        and data.get("bulk")
        and isinstance(data.get("stock_results"), list)
    ):
        # bulk dispatch：允许部分个股失败，仍保留 stock_results 供 expand / aggregate
        return JobResult(
            job_id=report.job_id,
            status=JobStatus.COMPLETED,
            result=data,
            error=report.error,
        )
    status = JobStatus.COMPLETED if report.success else JobStatus.FAILED
    return JobResult(
        job_id=report.job_id,
        status=status,
        result=data if report.success else None,
        error=report.error,
    )


def job_progress_payload(
    *,
    total_jobs: int,
    finished: int,
    completed_jobs: int,
    failed_jobs: int,
    last_job_id: str = "",
    last_job_status: str = "",
) -> Dict[str, Any]:
    """Workbench / CLI 进度回调 payload（全量累计）。"""
    pct = int(finished * 100 / total_jobs) if total_jobs else 100
    pct = min(100, max(0, pct))
    return {
        "progress_pct": pct,
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "cancelled_jobs": 0,
        "last_job_id": last_job_id,
        "last_job_status": last_job_status,
    }


__all__ = [
    "job_progress_payload",
    "job_report_to_job_result",
]
