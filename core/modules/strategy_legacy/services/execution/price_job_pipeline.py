"""价格因子模拟：BacktestEngine timeline dispatch job。"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from core.modules.backtest_engine.contracts import BacktestJob, JobContext, JobResult, JobStatus

from .engine_jobs import require_stock_id, wrap_timeline_stock_job
from .stock_job_pipeline import job_progress_payload, job_report_to_job_result

PRICE_TIMELINE_EXECUTOR_KEY = "strategy.price"

__all__ = [
    "PRICE_TIMELINE_EXECUTOR_KEY",
    "build_price_factor_payload",
    "execute_price_factor_job",
    "execute_price_factor_timeline_job",
    "expand_bulk_price_job_results",
    "run_price_factor_timeline_via_backtest_engine",
    "workbench_disk_progress",
]


def _dispatch_job_id(job: Dict[str, Any]) -> str:
    return str(job.get("job_id") or "price_job")


def build_price_factor_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    """Worker 入参（pickle 友好）；要求 ``stock_jobs``。"""
    stock_jobs = job.get("stock_jobs")
    if not isinstance(stock_jobs, list) or not stock_jobs:
        raise ValueError("price dispatch job 缺少非空 stock_jobs")
    payload = dict(job)
    payload.setdefault("job_id", _dispatch_job_id(job))
    payload["stock_ids"] = list(job.get("stock_ids") or [])
    payload["stock_jobs"] = [dict(row) for row in stock_jobs]
    return payload


def execute_price_factor_job(context: JobContext) -> Dict[str, Any]:
    """子进程执行入口（模块级，spawn 可 pickle）。"""
    from core.modules.strategy.engines.simulator.price_factor.worker import (
        run_price_factor_payload,
    )

    return run_price_factor_payload(context.payload, in_subprocess=True)


def _merge_price_factor_batch(entities: List[Dict[str, Any]], batch_job_id: str) -> Dict[str, Any]:
    rows = BacktestJob.batch_payloads(entities)
    base = dict(rows[0])
    stock_jobs = [dict(row) for row in rows]
    stock_ids = [require_stock_id(row, label="price entity payload") for row in rows]
    merged = {
        key: value
        for key, value in base.items()
        if key not in {"job_id", "stock_id", "stock_ids", "id", "payload"}
    }
    merged["job_id"] = batch_job_id
    merged["stock_jobs"] = stock_jobs
    merged["stock_ids"] = stock_ids
    return merged


def execute_price_factor_timeline_job(context: JobContext) -> Dict[str, Any]:
    """BacktestEngine timeline 子进程入口：batch dispatch job → price worker。"""
    payload = dict(context.payload)
    batch_entities = payload.get("jobs")
    if not isinstance(batch_entities, list) or not batch_entities:
        raise ValueError(
            "price timeline worker payload must include non-empty jobs list"
        )
    dispatch_job = _merge_price_factor_batch(batch_entities, context.job_id)
    return execute_price_factor_job(
        JobContext(
            job_id=context.job_id,
            payload=build_price_factor_payload(dispatch_job),
            task_name=context.task_name,
        )
    )


def expand_bulk_price_job_results(job_results: List[Any]) -> List[Any]:
    expanded: List[Any] = []
    for jr in job_results:
        result = getattr(jr, "result", None) or {}
        if not isinstance(result, dict) or not result.get("bulk"):
            expanded.append(jr)
            continue
        parent_id = getattr(jr, "job_id", "")
        for row in result.get("stock_results") or []:
            if not isinstance(row, dict):
                continue
            sid = str(row.get("stock_id") or "")
            ok = bool(row.get("success"))
            expanded.append(
                JobResult(
                    job_id=sid or parent_id,
                    status=JobStatus.COMPLETED if ok else JobStatus.FAILED,
                    result=row if ok else None,
                    error=None if ok else str(row.get("error") or "failed"),
                )
            )
    return expanded


def _progress_units_from_execute_report(report: Any) -> Tuple[int, int, int]:
    data = getattr(report, "data", None) or {}
    if not isinstance(data, dict) or not data.get("bulk"):
        return 0, 0, 0
    ok = fail = 0
    for row in data.get("stock_results") or []:
        if isinstance(row, dict) and row.get("success"):
            ok += 1
        else:
            fail += 1
    return ok + fail, ok, fail


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


def run_price_factor_timeline_via_backtest_engine(
    *,
    stock_jobs: List[Dict[str, Any]],
    total_stocks: Optional[int] = None,
    run_name: str = "price",
    on_workbench_progress: Optional[Callable[[float], None]] = None,
    duckdb_data_mgr: Any = None,
) -> List[JobResult]:
    """Strategy 侧：逐股 jobs → BacktestEngine timeline.run（内部 probe + plan + split）。"""
    from core.modules.backtest_engine import BacktestEngine
    from core.modules.backtest_engine.contracts import JobReport, RunCallbacks, RunProgress

    from core.modules.backtest_engine.core.performance.settings import (
        resolve_entity_based_performance,
    )
    from .worker_profile import profile_price_factor_dispatch_config

    n = total_stocks if total_stocks is not None else len(stock_jobs)
    engine_jobs: List[Dict[str, Any]] = []
    for job in stock_jobs:
        engine_jobs.append(wrap_timeline_stock_job(job))

    finished = 0
    ok_count = 0
    fail_count = 0

    def on_engine_result(report: JobReport, progress: RunProgress) -> None:
        nonlocal finished, ok_count, fail_count
        units, ok_u, fail_u = _progress_units_from_execute_report(report)
        if units:
            finished += units
            ok_count += ok_u
            fail_count += fail_u
        else:
            finished += 1
            if report.success:
                ok_count += 1
            else:
                fail_count += 1
        if on_workbench_progress is not None and n > 0:
            workbench_disk_progress(
                job_progress_payload(
                    total_jobs=n,
                    finished=finished,
                    completed_jobs=ok_count,
                    failed_jobs=fail_count,
                ),
                on_workbench_progress,
            )

    result = BacktestEngine.entity_based.run(
        engine_jobs,
        execute_price_factor_timeline_job,
        performance=resolve_entity_based_performance(profile_price_factor_dispatch_config()),
        task_name=run_name,
        callbacks=RunCallbacks(on_result=on_engine_result),
    )
    job_results = [job_report_to_job_result(report) for report in result.job_results]
    return expand_bulk_price_job_results(job_results)
