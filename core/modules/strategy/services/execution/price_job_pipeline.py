"""价格因子模拟：JobPipeline（PROCESS）多股 dispatch job。"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from core.infra.job_pipeline import JobContext
from core.infra.job_pipeline.probe import WorkerProbe
from core.infra.worker.multi_process.process_worker import JobResult, JobStatus

from .stock_job_pipeline import run_stock_jobs_via_pipeline

__all__ = [
    "build_price_factor_payload",
    "count_progress_units_from_price_job_result",
    "execute_price_factor_job",
    "expand_bulk_price_job_results",
    "run_price_factor_in_main_process",
    "run_price_factor_jobs_via_pipeline",
    "resolve_price_max_workers",
    "workbench_disk_progress",
]


def _dispatch_job_id(job: Dict[str, Any]) -> str:
    return str(job.get("job_id") or job.get("stock_id") or "price_job")


def build_price_factor_payload(job: Dict[str, Any]) -> Dict[str, Any]:
    """Worker 入参（pickle 友好）。"""
    payload = dict(job)
    payload.setdefault("job_id", _dispatch_job_id(job))
    stock_ids = job.get("stock_ids")
    if isinstance(stock_ids, list) and stock_ids:
        payload["stock_ids"] = list(stock_ids)
        if len(stock_ids) == 1 and not payload.get("stock_id"):
            payload["stock_id"] = stock_ids[0]
    stock_jobs = job.get("stock_jobs")
    if isinstance(stock_jobs, list) and stock_jobs:
        payload["stock_jobs"] = [dict(row) for row in stock_jobs]
    return payload


def execute_price_factor_job(context: JobContext) -> Dict[str, Any]:
    """子进程执行入口（模块级，spawn 可 pickle）。"""
    from core.modules.strategy.engines.simulator.price_factor.worker import (
        run_price_factor_payload,
    )

    return run_price_factor_payload(context.payload, in_subprocess=True)


def count_progress_units_from_price_job_result(job_result: Any) -> Tuple[int, int, int]:
    status = getattr(job_result, "status", None)
    status_value = getattr(status, "value", str(status))
    if str(status_value).lower() != "completed":
        data = getattr(job_result, "result", None) or {}
        if isinstance(data, dict) and data.get("bulk"):
            ids = data.get("stock_ids") or []
            n = len(ids) if isinstance(ids, list) else 1
            return n, 0, n
        return 1, 0, 1

    result = getattr(job_result, "result", None) or {}
    if not isinstance(result, dict):
        return 1, 0, 1
    if result.get("bulk") and isinstance(result.get("stock_results"), list):
        ok = fail = 0
        for row in result["stock_results"]:
            if isinstance(row, dict) and row.get("success"):
                ok += 1
            else:
                fail += 1
        return ok + fail, ok, fail
    if result.get("success"):
        return 1, 1, 0
    return 1, 0, 1


def expand_bulk_price_job_results(job_results: List[Any]) -> List[Any]:
    expanded: List[Any] = []
    for jr in job_results:
        result = getattr(jr, "result", None) or {}
        if not isinstance(result, dict) or not result.get("bulk"):
            expanded.append(jr)
            continue
        parent_id = getattr(jr, "job_id", "")
        status = getattr(jr, "status", None)
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
    if not isinstance(data, dict):
        ok = 1 if getattr(report, "success", False) else 0
        fail = 0 if ok else 1
        return ok + fail, ok, fail
    if data.get("bulk") and isinstance(data.get("stock_results"), list):
        ok = fail = 0
        for row in data["stock_results"]:
            if isinstance(row, dict) and row.get("success"):
                ok += 1
            else:
                fail += 1
        return ok + fail, ok, fail
    ok = 1 if data.get("success") else 0
    fail = 0 if ok else 1
    return ok + fail, ok, fail


def run_price_factor_in_main_process(
    dispatch_jobs: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """主进程 in-process batch（探针判定 N*C<O 时使用）。"""
    from core.modules.strategy.engines.simulator.price_factor.worker import (
        run_price_factor_payload,
    )

    if not dispatch_jobs:
        return []
    if len(dispatch_jobs) == 1:
        out = run_price_factor_payload(dispatch_jobs[0], in_subprocess=False)
        if out.get("bulk"):
            return list(out.get("stock_results") or [])
        return [out] if isinstance(out, dict) else []

    results: List[Dict[str, Any]] = []
    for job in dispatch_jobs:
        out = run_price_factor_payload(job, in_subprocess=False)
        if out.get("bulk"):
            results.extend(list(out.get("stock_results") or []))
        elif isinstance(out, dict):
            results.append(out)
    return results


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
    dispatch_jobs: List[Dict[str, Any]],
    max_workers: Any,
    total_stocks: Optional[int] = None,
    run_name: str = "price",
    on_workbench_progress: Optional[Callable[[float], None]] = None,
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
        elif job.get("stock_id"):
            total += 1
    return total
