"""价格因子模拟：JobPipeline（PROCESS）多股 dispatch job。"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from core.infra.job_pipeline import JobContext
from core.infra.job_pipeline.profile import WorkerProfiles, resolve_pipeline_workers
from core.infra.worker.multi_process.process_worker import JobResult, JobStatus

from .stock_job_pipeline import run_stock_jobs_via_pipeline

__all__ = [
    "build_price_factor_payload",
    "execute_price_factor_job",
    "expand_bulk_price_job_results",
    "run_price_factor_in_main_process",
    "run_price_factor_jobs_via_pipeline",
    "resolve_price_max_workers",
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


def run_price_factor_in_main_process(
    dispatch_jobs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """主进程 in-process batch（探针判定 N*C<O 时使用）。"""
    from core.modules.strategy.engines.simulator.price_factor.worker import (
        run_price_factor_payload,
    )

    results: List[Dict[str, Any]] = []
    for job in dispatch_jobs:
        out = run_price_factor_payload(job, in_subprocess=False)
        results.extend(list(out.get("stock_results") or []))
    return results


def resolve_price_max_workers(max_workers: Any) -> int:
    return resolve_pipeline_workers(worker_id=WorkerProfiles.PRICE_FACTOR)


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
    dispatch_jobs: List[Dict[str, Any]],
    max_workers: Any,
    total_stocks: Optional[int] = None,
    run_name: str = "price",
    on_workbench_progress: Optional[Callable[[float], None]] = None,
    duckdb_data_mgr: Any = None,
) -> List[JobResult]:
    """对 dispatch jobs 跑 JobPipeline；``total_stocks`` 为股票总数。"""
    n = total_stocks if total_stocks is not None else _count_stocks(dispatch_jobs)
    on_progress = None
    if on_workbench_progress is not None:
        on_progress = lambda p: workbench_disk_progress(p, on_workbench_progress)

    job_results = run_stock_jobs_via_pipeline(
        stock_jobs=dispatch_jobs,
        build_payload=build_price_factor_payload,
        execute=execute_price_factor_job,
        max_workers=resolve_price_max_workers(max_workers),
        total_jobs=n,
        run_name=run_name,
        on_job_progress=on_progress,
        progress_log_label="price",
        job_id_fn=_dispatch_job_id,
        progress_units_from_report=_progress_units_from_execute_report,
        worker_profile=WorkerProfiles.PRICE_FACTOR,
        duckdb_data_mgr=duckdb_data_mgr,
    )
    return expand_bulk_price_job_results(job_results)


def _count_stocks(jobs: List[Dict[str, Any]]) -> int:
    total = 0
    for job in jobs:
        ids = job.get("stock_ids")
        if isinstance(ids, list) and ids:
            total += len(ids)
        elif job.get("stock_jobs"):
            total += len(job.get("stock_jobs") or [])
    return total
