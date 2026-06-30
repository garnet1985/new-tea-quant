"""机会枚举：BacktestEngine timeline / sliced 执行入口。"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple

from core.modules.backtest_engine.core.shared.types import JobContext, JobResult, JobStatus

from core.modules.backtest_engine.core.shared.jobs import BacktestJob

from .engine_jobs import require_stock_id, wrap_slice_dispatch_job, wrap_timeline_stock_job
from .stock_job_pipeline import job_progress_payload, job_report_to_job_result

ENUM_TIMELINE_EXECUTOR_KEY = "strategy.enum"
ENUM_SLICED_EXECUTOR_KEY = "strategy.enum"

__all__ = [
    "ENUM_SLICED_EXECUTOR_KEY",
    "ENUM_TIMELINE_EXECUTOR_KEY",
    "build_enumeration_payload",
    "calendar_progress_units_from_execute_report",
    "count_progress_units_from_job_result",
    "execute_enumeration_job",
    "execute_enumeration_timeline_job",
    "expand_bulk_job_results",
    "job_report_to_job_result",
    "job_progress_payload",
    "run_enumeration_sliced_via_backtest_engine",
    "run_enumeration_timeline_via_backtest_engine",
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
        "_slice_plan",
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


def execute_enumeration_timeline_job(context: JobContext) -> Dict[str, Any]:
    """BacktestEngine timeline 子进程入口：batch payload → 枚举 worker。"""
    payload = dict(context.payload)
    batch_entities = payload.get("jobs")
    if not isinstance(batch_entities, list) or not batch_entities:
        raise ValueError(
            "enumeration timeline worker payload must include non-empty jobs list"
        )
    dispatch_job = _merge_enumeration_batch(batch_entities, context.job_id)
    global_extra_cache = (
        dispatch_job.get("_global_extra_cache")
        or payload.get("_global_extra_cache")
        or {}
    )
    enum_payload = build_enumeration_payload(dispatch_job, global_extra_cache)
    return execute_enumeration_job(
        JobContext(
            job_id=context.job_id,
            payload=enum_payload,
            run_name=context.run_name,
        )
    )


def _merge_enumeration_batch(
    entities: List[Dict[str, Any]],
    batch_job_id: str,
) -> Dict[str, Any]:
    from core.modules.strategy.engines.simulator.enumerator.stock_based.dispatch_jobs import (
        dispatch_job_id,
    )

    rows = BacktestJob.batch_payloads(entities)
    base = dict(rows[0])
    stock_ids = [require_stock_id(row, label="enumeration entity payload") for row in rows]

    merged = {
        key: value
        for key, value in base.items()
        if key not in {"job_id", "stock_id", "stock_ids", "id", "payload"}
    }
    merged["job_id"] = (
        dispatch_job_id(0, stock_ids)
        if len(stock_ids) > 1
        else stock_ids[0]
    )
    merged["stock_ids"] = stock_ids
    if len(stock_ids) == 1:
        merged["stock_id"] = stock_ids[0]
    merged["_global_extra_cache"] = base.get("_global_extra_cache")
    return merged


def run_enumeration_timeline_via_backtest_engine(
    *,
    entity_jobs: List[Dict[str, Any]],
    global_extra_cache: Dict[str, List[Dict[str, Any]]],
    total_jobs: int,
    run_name: str = "enum",
    finished_offset: int = 0,
    completed_offset: int = 0,
    failed_offset: int = 0,
    on_job_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    duckdb_data_mgr: Any = None,
    progress_units_from_report: Optional[
        Callable[[Any], Tuple[int, int, int]]
    ] = None,
) -> List[Any]:
    """Strategy 侧：组装 jobs + execute_fn，交给 BacktestEngine timeline.run。"""
    from pathlib import Path

    from core.modules.backtest_engine import BacktestEngine
    from core.modules.backtest_engine.core.shared.types import JobReport, RunProgress

    from .run_hooks import StrategyRunHooksCoordinator

    engine_jobs: List[Dict[str, Any]] = []
    for job in entity_jobs:
        engine_jobs.append(
            wrap_timeline_stock_job(job, _global_extra_cache=global_extra_cache)
        )

    units_fn = progress_units_from_report or _progress_units_from_execute_report
    stock_finished = finished_offset
    stock_ok = completed_offset
    stock_fail = failed_offset
    progress_meta = {"last_job_id": "", "last_job_status": ""}

    run_hooks: Optional[StrategyRunHooksCoordinator] = None
    if entity_jobs:
        try:
            sample = entity_jobs[0]
            output_dir = sample.get("output_dir")
            run_hooks = StrategyRunHooksCoordinator.from_job(
                sample,
                run_name=run_name,
                output_dir=Path(output_dir) if output_dir else None,
                total_entities=total_jobs,
                execution_mode="entity_timeline",
            )
            run_hooks.on_run_start()
        except Exception:
            run_hooks = None

    def on_engine_result(report: JobReport, progress: RunProgress) -> None:
        nonlocal stock_finished, stock_ok, stock_fail
        progress_meta["last_job_id"] = report.job_id
        progress_meta["last_job_status"] = "completed" if report.success else "failed"
        if run_hooks is not None:
            run_hooks.on_batch_finish(
                str(report.job_id),
                _stock_ids_from_job_report(report),
                report=report,
                progress=progress,
            )
        units, ok_u, fail_u = units_fn(report)
        stock_finished += units
        stock_ok += ok_u
        stock_fail += fail_u
        if on_job_progress is not None:
            on_job_progress(
                job_progress_payload(
                    total_jobs=total_jobs,
                    finished=stock_finished,
                    completed_jobs=stock_ok,
                    failed_jobs=stock_fail,
                    last_job_id=progress_meta["last_job_id"],
                    last_job_status=progress_meta["last_job_status"],
                )
            )

    result = BacktestEngine.timeline.run(
        engine_jobs,
        execute_enumeration_timeline_job,
        executor_key=ENUM_TIMELINE_EXECUTOR_KEY,
        run_name=run_name,
        on_result=on_engine_result,
        data_mgr=duckdb_data_mgr,
        log_label="enum",
    )
    if run_hooks is not None:
        run_hooks.on_run_finish()
    return [job_report_to_job_result(report) for report in result.job_results]


def execute_enumeration_sliced_job(context: JobContext) -> Dict[str, Any]:
    """BacktestEngine sliced 子进程入口：注入 slice plan → calendar_slice orchestrator。"""
    from core.modules.strategy.services.execution.worker_runtime import (
        bootstrap_strategy_worker_data_manager,
        release_strategy_worker_runtime,
    )

    bootstrap_strategy_worker_data_manager()
    try:
        payload = dict(context.payload)
        engine_keys = frozenset({"_slice_plan", "_job_id", "_run_name", "_executor"})
        dispatch_job = {
            key: value
            for key, value in payload.items()
            if key in engine_keys or not str(key).startswith("_")
        }
        global_extra_cache = (
            dispatch_job.pop("_global_extra_cache", None)
            or payload.get("_global_extra_cache")
            or {}
        )
        enum_payload = build_enumeration_payload(dispatch_job, global_extra_cache)
        return execute_enumeration_job(
            JobContext(
                job_id=context.job_id,
                payload=enum_payload,
                run_name=context.run_name,
            )
        )
    finally:
        release_strategy_worker_runtime()


def run_enumeration_sliced_via_backtest_engine(
    *,
    dispatch_jobs: List[Dict[str, Any]],
    global_extra_cache: Dict[str, List[Dict[str, Any]]],
    total_jobs: int,
    run_name: str = "enum",
    finished_offset: int = 0,
    completed_offset: int = 0,
    failed_offset: int = 0,
    on_job_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    duckdb_data_mgr: Any = None,
    progress_units_from_report: Optional[
        Callable[[Any], Tuple[int, int, int]]
    ] = None,
) -> List[Any]:
    """Strategy calendar_slice：单 bulk job → BacktestEngine.sliced.run。"""
    from core.modules.backtest_engine import BacktestEngine
    from core.modules.backtest_engine.core.shared.types import JobReport, RunProgress

    engine_jobs: List[Dict[str, Any]] = []
    for job in dispatch_jobs:
        engine_jobs.append(
            wrap_slice_dispatch_job(job, _global_extra_cache=global_extra_cache)
        )

    units_fn = progress_units_from_report or calendar_progress_units_from_execute_report
    stock_finished = finished_offset
    stock_ok = completed_offset
    stock_fail = failed_offset
    progress_meta = {"last_job_id": "", "last_job_status": ""}

    def on_engine_result(report: JobReport, progress: RunProgress) -> None:
        nonlocal stock_finished, stock_ok, stock_fail
        progress_meta["last_job_id"] = report.job_id
        progress_meta["last_job_status"] = "completed" if report.success else "failed"
        units, ok_u, fail_u = units_fn(report)
        stock_finished += units
        stock_ok += ok_u
        stock_fail += fail_u
        if on_job_progress is not None:
            on_job_progress(
                job_progress_payload(
                    total_jobs=total_jobs,
                    finished=stock_finished,
                    completed_jobs=stock_ok,
                    failed_jobs=stock_fail,
                    last_job_id=progress_meta["last_job_id"],
                    last_job_status=progress_meta["last_job_status"],
                )
            )

    result = BacktestEngine.sliced.run(
        engine_jobs,
        execute_enumeration_sliced_job,
        executor_key=ENUM_SLICED_EXECUTOR_KEY,
        run_name=run_name,
        on_result=on_engine_result,
        data_mgr=duckdb_data_mgr,
        log_label="enum-sliced",
    )
    return [job_report_to_job_result(report) for report in result.job_results]


def _stock_ids_from_job_report(report: Any) -> List[str]:
    data = getattr(report, "data", None) or {}
    if isinstance(data, dict):
        if data.get("bulk") and isinstance(data.get("stock_results"), list):
            ids = [
                str(row.get("stock_id") or "").strip()
                for row in data["stock_results"]
                if isinstance(row, dict) and str(row.get("stock_id") or "").strip()
            ]
            if ids:
                return ids
        sid = str(data.get("stock_id") or "").strip()
        if sid:
            return [sid]
    job_id = str(getattr(report, "job_id", "") or "").strip()
    return [job_id] if job_id else []


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
