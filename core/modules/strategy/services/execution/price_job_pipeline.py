"""价格因子模拟：JobPipeline（PROCESS）单股单 job。"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from core.infra.job_pipeline import JobContext
from core.infra.job_pipeline.probe import WorkerProbe
from core.infra.worker.multi_process.process_worker import JobResult

from .stock_job_pipeline import run_stock_jobs_via_pipeline


def build_price_factor_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    """Worker 入参（与原 ProcessWorker ``payload`` 一致）。"""
    return dict(job)


def execute_price_factor_job(context: JobContext) -> Dict[str, Any]:
    """子进程执行入口（模块级，spawn 可 pickle）。"""
    from core.modules.strategy.engines.simulator.price_factor.worker import PriceFactorWorker
    from core.modules.strategy.services.execution.worker_runtime import (
        bootstrap_strategy_worker_data_manager,
        release_strategy_worker_runtime,
    )

    bootstrap_strategy_worker_data_manager()
    try:
        return PriceFactorWorker.execute_job(context.payload)
    finally:
        release_strategy_worker_runtime()


def resolve_price_max_workers(max_workers: Any) -> int:
    return WorkerProbe.resolve(max_workers)


def workbench_disk_progress(
    payload: Dict[str, Any],
    progress_callback: Callable[[float], None],
) -> None:
    """将 job ``progress_pct`` 映射为工作台磁盘进度 15%～88%。"""
    try:
        w = float(payload.get("progress_pct") or 0)
    except (TypeError, ValueError):
        w = 0.0
    disk = 15.0 + (max(0.0, min(100.0, w)) / 100.0) * 73.0
    progress_callback(min(88.0, disk))


def run_price_factor_jobs_via_pipeline(
    *,
    stock_jobs: List[Dict[str, Any]],
    max_workers: Any,
    total_jobs: Optional[int] = None,
    run_name: str = "price",
    on_workbench_progress: Optional[Callable[[float], None]] = None,
) -> List[JobResult]:
    """对单股价格任务跑 JobPipeline，返回 JobResult 列表。"""
    n = total_jobs if total_jobs is not None else len(stock_jobs)
    on_progress = None
    if on_workbench_progress is not None:
        on_progress = lambda p: workbench_disk_progress(p, on_workbench_progress)

    return run_stock_jobs_via_pipeline(
        stock_jobs=stock_jobs,
        build_payload=build_price_factor_payload,
        execute=execute_price_factor_job,
        max_workers=resolve_price_max_workers(max_workers),
        total_jobs=n,
        run_name=run_name,
        on_job_progress=on_progress,
        progress_log_label="price",
    )
