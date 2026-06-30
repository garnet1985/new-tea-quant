"""扫描器：BacktestEngine timeline 单股 job。"""
from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from core.modules.backtest_engine.contracts import BacktestJob, JobContext, JobResult, RunCallbacks

from .engine_jobs import wrap_timeline_stock_job
from .runners.scanner_runner import run_scanner_payload
from .stock_job_pipeline import job_progress_payload, job_report_to_job_result

logger = logging.getLogger(__name__)

SCANNER_TIMELINE_EXECUTOR_KEY = "strategy.scanner"

__all__ = [
    "SCANNER_TIMELINE_EXECUTOR_KEY",
    "build_scanner_payload",
    "execute_scanner_job",
    "execute_scanner_timeline_job",
    "run_scanner_timeline_via_backtest_engine",
    "run_scanner_worker_payload",
]


def build_scanner_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    """Worker 入参（与原 ProcessWorker ``payload`` 一致）。"""
    return dict(job)


def run_scanner_worker_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """策略 scan 单股（主进程调试与子进程共用）。"""
    stock_id = str(payload.get("stock_id") or "")
    try:
        return run_scanner_payload(payload)
    except Exception as exc:
        logger.error("[Scanner] stock scan failed: %s - %s", stock_id, exc, exc_info=True)
        return {
            "success": False,
            "stock_id": stock_id,
            "opportunity": None,
            "error": str(exc),
        }


def execute_scanner_timeline_job(context: JobContext) -> Dict[str, Any]:
    """BacktestEngine timeline 子进程入口。"""
    from core.modules.strategy.services.execution.worker_runtime import (
        bootstrap_strategy_worker_data_manager,
        release_strategy_worker_runtime,
    )

    bootstrap_strategy_worker_data_manager()
    try:
        payload = dict(context.payload)
        batch_entities = payload.get("jobs")
        if not isinstance(batch_entities, list) or not batch_entities:
            raise ValueError(
                "scanner timeline worker payload must include non-empty jobs list"
            )
        stock_results: List[Dict[str, Any]] = []
        for row in BacktestJob.batch_payloads(batch_entities):
            stock_results.append(run_scanner_worker_payload(row))
        if len(stock_results) == 1:
            return stock_results[0]
        ok = all(bool(row.get("success")) for row in stock_results)
        return {
            "success": ok,
            "bulk": True,
            "stock_results": stock_results,
        }
    finally:
        release_strategy_worker_runtime()


def execute_scanner_job(context: JobContext) -> Dict[str, Any]:
    """子进程执行入口（模块级，spawn 可 pickle）。"""
    return execute_scanner_timeline_job(context)


def run_scanner_timeline_via_backtest_engine(
    *,
    stock_jobs: List[Dict[str, Any]],
    total_jobs: Optional[int] = None,
    run_name: str = "scanner",
    on_job_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    duckdb_data_mgr: Any = None,
) -> List[JobResult]:
    """Strategy 侧：扫描 jobs + execute_fn → BacktestEngine timeline.run。"""
    from core.modules.backtest_engine import BacktestEngine
    from core.modules.backtest_engine.contracts import JobReport, RunProgress

    from .worker_profile import profile_scanner_dispatch_config

    n = total_jobs if total_jobs is not None else len(stock_jobs)
    engine_jobs: List[Dict[str, Any]] = []
    for job in stock_jobs:
        engine_jobs.append(wrap_timeline_stock_job(job))

    finished = 0
    ok_count = 0
    fail_count = 0
    progress_meta = {"last_job_id": "", "last_job_status": ""}

    def on_engine_result(report: JobReport, progress: RunProgress) -> None:
        nonlocal finished, ok_count, fail_count
        progress_meta["last_job_id"] = report.job_id
        progress_meta["last_job_status"] = "completed" if report.success else "failed"
        data = report.data if isinstance(report.data, dict) else {}
        if data.get("bulk") and isinstance(data.get("stock_results"), list):
            for row in data["stock_results"]:
                finished += 1
                if isinstance(row, dict) and row.get("success"):
                    ok_count += 1
                else:
                    fail_count += 1
        else:
            finished += 1
            if report.success:
                ok_count += 1
            else:
                fail_count += 1
        if on_job_progress is not None:
            on_job_progress(
                job_progress_payload(
                    total_jobs=n,
                    finished=finished,
                    completed_jobs=ok_count,
                    failed_jobs=fail_count,
                    last_job_id=progress_meta["last_job_id"],
                    last_job_status=progress_meta["last_job_status"],
                )
            )

    result = BacktestEngine.entity_based.run(
        engine_jobs,
        execute_scanner_timeline_job,
        performance=profile_scanner_dispatch_config(),
        task_name=run_name,
        callbacks=RunCallbacks(on_result=on_engine_result),
    )
    return [job_report_to_job_result(report) for report in result.job_results]
