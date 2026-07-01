"""枚举器机器侧 runtime：配置 + 状态 + job 结果辅助。"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.contracts import JobReport, JobResult, JobStatus


@dataclass
class RuntimeContext:
    """调度与持久化配置（run 前确定）。"""

    strategy_name: str
    execution_mode: str
    start_date: str
    end_date: str
    jobs: List[Dict[str, Any]] = field(default_factory=list)
    output_dir: Optional[Path] = None
    version_id: Optional[int] = None
    version_dir_name: str = ""
    fingerprint_hash: str = ""
    settings_diff: Dict[str, Any] = field(default_factory=dict)
    disk_settings: Dict[str, Any] = field(default_factory=dict)
    worker_ref: Dict[str, str] = field(default_factory=dict)
    global_data_meta: Dict[str, Any] = field(default_factory=dict)
    task_name: str = ""
    run_name: str = ""
    performance: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeStatus:
    """运行过程可变状态。"""

    stage: str = "init"
    hook_stage: Optional[str] = None
    progress: Dict[str, Any] = field(default_factory=dict)
    monitor: Dict[str, Any] = field(default_factory=dict)
    job_results: List[Any] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)
    started_at: float = 0.0
    elapsed_seconds: float = 0.0


@dataclass
class EnumeratorRuntime:
    """context + status bundle。"""

    context: RuntimeContext
    status: RuntimeStatus


class JobResultHelper:
    """BacktestEngine JobReport 转换与进度 payload。"""

    @staticmethod
    def to_job_result(report: JobReport) -> JobResult:
        data = report.data
        if (
            isinstance(data, dict)
            and data.get("bulk")
            and isinstance(data.get("stock_results"), list)
        ):
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

    @staticmethod
    def progress_payload(
        *,
        total_jobs: int,
        finished: int,
        completed_jobs: int,
        failed_jobs: int,
        last_job_id: str = "",
        last_job_status: str = "",
    ) -> Dict[str, Any]:
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
    "EnumeratorRuntime",
    "JobResultHelper",
    "RuntimeContext",
    "RuntimeStatus",
]
