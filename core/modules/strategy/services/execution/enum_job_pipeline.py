"""机会枚举：JobPipeline（PROCESS）单股或多股 dispatch job。"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from core.infra.job_pipeline import JobContext
from core.infra.job_pipeline.profile import WorkerProfiles
from core.infra.worker.multi_process.process_worker import JobResult, JobStatus

from .stock_job_pipeline import (
    job_report_to_job_result,
    job_progress_from_run,
    job_progress_payload,
    run_stock_jobs_via_pipeline,
)

__all__ = [
    "build_enumeration_payload",
    "calendar_progress_units_from_execute_report",
    "count_progress_units_from_job_result",
    "execute_enumeration_job",
    "expand_bulk_job_results",
    "job_report_to_job_result",
    "job_progress_payload",
    "job_progress_from_run",
    "run_enumeration_jobs_via_pipeline",
]


def _dispatch_job_id(job: Dict[str, Any]) -> str:
    return str(job.get("job_id") or job.get("stock_id") or "enum_job")


def build_enumeration_payload(
    job: Dict[str, Any],
    global_extra_cache: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """Worker 入参（pickle 友好）。"""
    payload: Dict[str, Any] = {
        "job_id": _dispatch_job_id(job),
        "strategy_name": job["strategy_name"],
        "settings": job["settings"],
        "start_date": job["start_date"],
        "end_date": job["end_date"],
        "output_dir": job["output_dir"],
        "global_extra_cache": global_extra_cache,
        "backtest_calendar": job.get("backtest_calendar"),
        "worker_module_path": job["worker_module_path"],
        "worker_class_name": job["worker_class_name"],
        "worker_file_path": str(job.get("worker_file_path") or ""),
    }
    stock_ids = job.get("stock_ids")
    if isinstance(stock_ids, list) and stock_ids:
        payload["stock_ids"] = list(stock_ids)
        if len(stock_ids) == 1:
            payload["stock_id"] = stock_ids[0]
    else:
        payload["stock_id"] = job["stock_id"]
    mode = job.get("enumeration_execution_mode")
    if mode:
        payload["enumeration_execution_mode"] = mode
    if "slice_open_days" in job:
        payload["slice_open_days"] = job["slice_open_days"]
    for key in (
        "calendar_progress_mode",
        "calendar_progress_total",
        "progress_axis",
        "entity_progress_mode",
        "entity_progress_total",
        "workbench_strategy_name",
        "workbench_run_id",
        "stock_infos",
    ):
        if key in job and job.get(key) not in (None, ""):
            payload[key] = job[key]
    return payload


def count_progress_units_from_job_result(job_result: Any) -> Tuple[int, int]:
    """返回 (成功股数, 失败股数)。"""
    status = getattr(job_result, "status", None)
    status_value = getattr(status, "value", str(status))
    if str(status_value).lower() != "completed":
        data = getattr(job_result, "result", None) or {}
        if isinstance(data, dict) and data.get("bulk"):
            ids = data.get("stock_ids") or []
            return 0, len(ids) if isinstance(ids, list) else 1
        return 0, 1

    result = getattr(job_result, "result", None) or {}
    if not isinstance(result, dict):
        return 0, 1
    if result.get("bulk") and isinstance(result.get("stock_results"), list):
        ok = fail = 0
        for row in result["stock_results"]:
            if isinstance(row, dict) and row.get("success"):
                ok += 1
            else:
                fail += 1
        return ok, fail
    if result.get("success"):
        return 1, 0
    return 0, 1


def expand_bulk_job_results(job_results: List[Any]) -> List[Any]:
    """将多股 job 的 bulk 结果展开为每股一个 JobResult（供 aggregate 使用）。"""
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


def execute_enumeration_job(context: JobContext) -> Dict[str, Any]:
    """子进程执行入口（模块级，spawn 可 pickle）。"""
    from core.modules.strategy.services.execution.worker_runtime import (
        bootstrap_strategy_worker_data_manager,
        release_strategy_worker_runtime,
    )

    bootstrap_strategy_worker_data_manager()
    try:
        payload = context.payload
        if payload.get("enumeration_execution_mode") == "calendar_slice":
            from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.worker import (
                run_calendar_slice_enumeration_payload,
            )

            return run_calendar_slice_enumeration_payload(payload)
        from core.modules.strategy.engines.simulator.enumerator.stock_based.worker import (
            run_enumeration_payload,
        )

        return run_enumeration_payload(payload)
    finally:
        release_strategy_worker_runtime()


def calendar_progress_units_from_execute_report(report: Any) -> Tuple[int, int, int]:
    """calendar_slice 单 job 完成时按 slice/open_date 计进度单位。"""
    data = getattr(report, "data", None) or {}
    if isinstance(data, dict):
        cal = data.get("calendar_progress") or {}
        total = int(cal.get("total") or 0)
        if total > 0:
            ok = total if data.get("success") else 0
            fail = 0 if data.get("success") else total
            return ok + fail, ok, fail
    return _progress_units_from_execute_report(report)


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
    on_job_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    log_progress: bool = True,
    duckdb_data_mgr: Any = None,
    progress_units_from_report: Optional[
        Callable[[Any], Tuple[int, int, int]]
    ] = None,
) -> List[Any]:
    """
    对 dispatch jobs 跑 JobPipeline（QUEUE + PROCESS）。

    ``total_jobs`` 为股票总数（非 dispatch job 数）。
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
        on_job_progress=on_job_progress,
        log_progress=log_progress,
        progress_log_label="enum",
        job_id_fn=_dispatch_job_id,
        progress_units_from_report=progress_units_from_report
        or _progress_units_from_execute_report,
        worker_profile=WorkerProfiles.ENUMERATOR,
        duckdb_data_mgr=duckdb_data_mgr,
    )


def _progress_units_from_execute_report(report: Any) -> Tuple[int, int, int]:
    """(finished_units, ok_units, fail_units) from JobReport."""
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
