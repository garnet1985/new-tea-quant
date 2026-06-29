"""价格因子模拟：BacktestEngine timeline dispatch job。"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from core.infra.job_pipeline import JobContext
from core.infra.worker.multi_process.process_worker import JobResult, JobStatus

from .stock_job_pipeline import job_progress_payload, job_report_to_job_result

PRICE_TIMELINE_EXECUTOR_KEY = "strategy.price"

__all__ = [
    "PRICE_TIMELINE_EXECUTOR_KEY",
    "build_price_factor_payload",
    "execute_price_factor_job",
    "execute_price_factor_timeline_job",
    "expand_bulk_price_job_results",
    "run_price_factor_in_main_process",
    "run_price_factor_jobs_via_pipeline",
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


def _normalize_price_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    """BacktestEngine timeline jobs 可能是 ``{id, payload}`` 包装或 flat dispatch row。"""
    nested = entity.get("payload")
    if isinstance(nested, dict):
        return dict(nested)
    return dict(entity)


def _merge_price_factor_batch(entities: List[Dict[str, Any]], batch_job_id: str) -> Dict[str, Any]:
    if not entities:
        raise ValueError("price timeline batch is empty")
    normalized = [_normalize_price_entity(entity) for entity in entities]
    base = dict(normalized[0])
    stock_jobs: List[Dict[str, Any]] = []
    stock_ids: List[str] = []
    for entity in normalized:
        rows = entity.get("stock_jobs")
        if isinstance(rows, list):
            stock_jobs.extend(dict(row) for row in rows if isinstance(row, dict))
        ids = entity.get("stock_ids")
        if isinstance(ids, list):
            stock_ids.extend(str(s).strip() for s in ids if str(s).strip())
    if not stock_jobs:
        raise ValueError("price timeline batch has no stock_jobs")
    merged = {
        key: value
        for key, value in base.items()
        if key not in {"job_id", "stock_jobs", "stock_ids", "id", "payload"}
    }
    merged["job_id"] = batch_job_id
    merged["stock_jobs"] = stock_jobs
    merged["stock_ids"] = stock_ids or [str(j.get("stock_id") or "") for j in stock_jobs]
    return merged


def execute_price_factor_timeline_job(context: JobContext) -> Dict[str, Any]:
    """BacktestEngine timeline 子进程入口：batch dispatch job → price worker。"""
    payload = dict(context.payload)
    batch_entities = payload.get("jobs")
    if isinstance(batch_entities, list) and batch_entities:
        dispatch_job = _merge_price_factor_batch(batch_entities, context.job_id)
    else:
        dispatch_job = {
            key: value
            for key, value in payload.items()
            if not str(key).startswith("_")
        }
    return execute_price_factor_job(
        JobContext(
            job_id=context.job_id,
            payload=build_price_factor_payload(dispatch_job),
            run_name=context.run_name,
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
    dispatch_jobs: List[Dict[str, Any]],
    total_stocks: Optional[int] = None,
    run_name: str = "price",
    on_workbench_progress: Optional[Callable[[float], None]] = None,
    duckdb_data_mgr: Any = None,
) -> List[JobResult]:
    """Strategy 侧：price dispatch jobs → BacktestEngine timeline.run。"""
    from core.modules.backtest_engine import BacktestEngine
    from core.modules.backtest_engine.core.shared.types import JobReport, RunProgress

    n = total_stocks if total_stocks is not None else _count_stocks(dispatch_jobs)
    engine_jobs: List[Dict[str, Any]] = []
    for job in dispatch_jobs:
        job_id = _dispatch_job_id(job)
        engine_jobs.append({"id": job_id, "payload": dict(job)})

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

    result = BacktestEngine.timeline.run(
        engine_jobs,
        execute_price_factor_timeline_job,
        executor_key=PRICE_TIMELINE_EXECUTOR_KEY,
        run_name=run_name,
        on_result=on_engine_result,
        data_mgr=duckdb_data_mgr,
        log_label="price",
    )
    job_results = [job_report_to_job_result(report) for report in result.job_results]
    return expand_bulk_price_job_results(job_results)


def run_price_factor_jobs_via_pipeline(
    *,
    dispatch_jobs: List[Dict[str, Any]],
    max_workers: Any,
    total_stocks: Optional[int] = None,
    run_name: str = "price",
    on_workbench_progress: Optional[Callable[[float], None]] = None,
    duckdb_data_mgr: Any = None,
) -> List[JobResult]:
    """对 dispatch jobs 跑 BacktestEngine timeline；``total_stocks`` 为股票总数。"""
    _ = max_workers
    return run_price_factor_timeline_via_backtest_engine(
        dispatch_jobs=dispatch_jobs,
        total_stocks=total_stocks,
        run_name=run_name,
        on_workbench_progress=on_workbench_progress,
        duckdb_data_mgr=duckdb_data_mgr,
    )


def _count_stocks(jobs: List[Dict[str, Any]]) -> int:
    total = 0
    for job in jobs:
        ids = job.get("stock_ids")
        if isinstance(ids, list) and ids:
            total += len(ids)
        elif job.get("stock_jobs"):
            total += len(job.get("stock_jobs") or [])
    return total
