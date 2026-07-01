"""Layer 3：回测 runtime 上下文 + 运行状态 bundle。"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.modules.backtest_engine.contracts import JobReport, JobResult, JobStatus

from .strategy_context import StrategyContext


@dataclass
class BacktestRuntimeContext(StrategyContext):
    """回测执行期上下文：在 ``StrategyContext`` 上追加 jobs / performance 等 runtime 字段。"""

    execution_mode: str = ""
    jobs: List[Dict[str, Any]] = field(default_factory=list)
    global_data_meta: Dict[str, Any] = field(default_factory=dict)
    task_name: str = ""
    run_name: str = ""
    performance: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_strategy_context(
        cls,
        strategy: StrategyContext,
        *,
        execution_mode: str,
        jobs: List[Dict[str, Any]],
        task_name: str,
        run_name: str,
        performance: Dict[str, Any],
        global_data_meta: Optional[Dict[str, Any]] = None,
    ) -> BacktestRuntimeContext:
        return cls(
            key=strategy.key,
            id=strategy.id,
            strategies_root=strategy.strategies_root,
            folder=strategy.folder,
            strategy_file=strategy.strategy_file,
            settings_file=strategy.settings_file,
            settings=strategy.settings,
            worker_class=strategy.worker_class,
            worker_module_path=strategy.worker_module_path,
            worker_class_name=strategy.worker_class_name,
            worker_file_path=strategy.worker_file_path,
            userspace_root=strategy.userspace_root,
            effective_settings=strategy.effective_settings,
            settings_diff=strategy.settings_diff,
            start_date=strategy.start_date,
            end_date=strategy.end_date,
            entity_ids=list(strategy.entity_ids),
            fingerprint_hash=strategy.fingerprint_hash,
            output_dir=strategy.output_dir,
            version_id=strategy.version_id,
            version_dir_name=strategy.version_dir_name,
            execution_mode=execution_mode,
            jobs=list(jobs),
            global_data_meta=dict(global_data_meta or {}),
            task_name=task_name,
            run_name=run_name,
            performance=dict(performance),
        )


@dataclass
class RuntimeStatus:
    """运行过程可变状态（与 context 分离）。"""

    stage: str = "init"
    hook_stage: Optional[str] = None
    progress: Dict[str, Any] = field(default_factory=dict)
    monitor: Dict[str, Any] = field(default_factory=dict)
    job_results: List[Any] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)
    started_at: float = 0.0
    elapsed_seconds: float = 0.0


@dataclass
class BacktestRuntime:
    """context + status bundle。"""

    context: BacktestRuntimeContext
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


# Backward-compat aliases
RuntimeContext = BacktestRuntimeContext
EnumeratorRuntime = BacktestRuntime


__all__ = [
    "BacktestRuntime",
    "BacktestRuntimeContext",
    "EnumeratorRuntime",
    "JobResultHelper",
    "RuntimeContext",
    "RuntimeStatus",
]
