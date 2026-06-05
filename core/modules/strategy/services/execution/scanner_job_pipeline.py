"""扫描器：JobPipeline（PROCESS）单股单 job。"""
from __future__ import annotations

import importlib
import logging
from typing import Any, Callable, Dict, List, Optional

from core.infra.job_pipeline import JobContext
from core.infra.job_pipeline.profile import WorkerProfiles, resolve_pipeline_workers
from core.infra.worker.multi_process.process_worker import JobResult

from .stock_job_pipeline import run_stock_jobs_via_pipeline

logger = logging.getLogger(__name__)


def build_scanner_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    """Worker 入参（与原 ProcessWorker ``payload`` 一致）。"""
    return dict(job)


def run_scanner_worker_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """策略 Worker 扫描单股（主进程调试与子进程共用）。"""
    stock_id = str(payload.get("stock_id") or "")
    try:
        worker_module = importlib.import_module(str(payload["worker_module_path"]))
        worker_class = getattr(worker_module, str(payload["worker_class_name"]))
        return worker_class(payload).run()
    except Exception as exc:
        logger.error("[Scanner] stock scan failed: %s - %s", stock_id, exc, exc_info=True)
        return {
            "success": False,
            "stock_id": stock_id,
            "opportunity": None,
            "error": str(exc),
        }


def execute_scanner_job(context: JobContext) -> Dict[str, Any]:
    """子进程执行入口（模块级，spawn 可 pickle）。"""
    from core.modules.strategy.services.execution.worker_runtime import (
        bootstrap_strategy_worker_data_manager,
        release_strategy_worker_runtime,
    )

    bootstrap_strategy_worker_data_manager()
    try:
        return run_scanner_worker_payload(context.payload)
    finally:
        release_strategy_worker_runtime()


def resolve_scanner_max_workers(max_workers: Any) -> int:
    return resolve_pipeline_workers(worker_id=WorkerProfiles.SCANNER)


def run_scanner_jobs_via_pipeline(
    *,
    stock_jobs: List[Dict[str, Any]],
    max_workers: Any,
    total_jobs: Optional[int] = None,
    run_name: str = "scanner",
    on_job_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> List[JobResult]:
    """对单股扫描任务跑 JobPipeline，返回 JobResult 列表。"""
    n = total_jobs if total_jobs is not None else len(stock_jobs)
    return run_stock_jobs_via_pipeline(
        stock_jobs=stock_jobs,
        build_payload=build_scanner_payload,
        execute=execute_scanner_job,
        max_workers=resolve_scanner_max_workers(max_workers),
        total_jobs=n,
        run_name=run_name,
        on_job_progress=on_job_progress,
        progress_log_label="scanner",
        worker_profile=WorkerProfiles.SCANNER,
    )
