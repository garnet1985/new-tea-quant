"""机会枚举：JobPipeline（PROCESS）单股单 job。"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from core.infra.job_pipeline import JobContext

from .stock_job_pipeline import (
    job_report_to_job_result,
    legacy_progress_from_counts,
    legacy_progress_from_run_progress,
    run_stock_jobs_via_pipeline,
)

__all__ = [
    "build_enumeration_payload",
    "execute_enumeration_job",
    "job_report_to_job_result",
    "legacy_progress_from_counts",
    "legacy_progress_from_run_progress",
    "run_enumeration_jobs_via_pipeline",
]


def build_enumeration_payload(
    job: Dict[str, Any],
    global_extra_cache: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Worker 入参（与原 ProcessExecutor ``data`` 字段一致）。"""
    return {
        "stock_id": job["stock_id"],
        "strategy_name": job["strategy_name"],
        "settings": job["settings"],
        "start_date": job["start_date"],
        "end_date": job["end_date"],
        "output_dir": job["output_dir"],
        "global_extra_cache": global_extra_cache,
        "backtest_calendar": job.get("backtest_calendar"),
        "worker_module_path": job["worker_module_path"],
        "worker_class_name": job["worker_class_name"],
    }


def execute_enumeration_job(context: JobContext) -> Dict[str, Any]:
    """子进程执行入口（模块级，spawn 可 pickle）。"""
    from core.modules.strategy.engines.simulator.enumerator.worker import (
        OpportunityEnumeratorWorker,
    )
    from core.modules.strategy.services.execution.worker_runtime import (
        bootstrap_strategy_worker_data_manager,
        release_strategy_worker_runtime,
    )

    bootstrap_strategy_worker_data_manager()
    try:
        return OpportunityEnumeratorWorker(context.payload).run()
    finally:
        release_strategy_worker_runtime()


def run_enumeration_jobs_via_pipeline(
    *,
    stock_jobs: List[Dict[str, Any]],
    global_extra_cache: Dict[str, List[Dict[str, Any]]],
    max_workers: int,
    total_jobs: int,
    run_name: str = "enum",
    finished_offset: int = 0,
    completed_offset: int = 0,
    failed_offset: int = 0,
    on_legacy_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    log_progress: bool = True,
) -> List[Any]:
    """
    对一批单股任务跑 JobPipeline（QUEUE + PROCESS），返回与旧 ProcessExecutor 兼容的 JobResult 列表。
    """
    return run_stock_jobs_via_pipeline(
        stock_jobs=stock_jobs,
        build_payload=lambda job: build_enumeration_payload(job, global_extra_cache),
        execute=execute_enumeration_job,
        max_workers=max_workers,
        total_jobs=total_jobs,
        run_name=run_name,
        finished_offset=finished_offset,
        completed_offset=completed_offset,
        failed_offset=failed_offset,
        on_legacy_progress=on_legacy_progress,
        log_progress=log_progress,
        progress_log_label="enum",
    )
