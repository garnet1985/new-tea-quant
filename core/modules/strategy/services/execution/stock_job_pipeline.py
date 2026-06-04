"""Strategy 多股 dispatch JobPipeline 公共调度（enum / price 等）。"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

PROGRESS_LOG_INTERVAL_SEC = 45
PROGRESS_LOG_EVERY_N = 50

from core.infra.job_pipeline import (
    Job,
    JobContext,
    JobPipeline,
    JobPipelineSettings,
    JobReport,
    RunProgress,
)
from core.infra.job_pipeline.types import ExecuteMode, ExecutionBackend, JobFailurePhase
from core.infra.job_pipeline.worker_profile import WorkerProfiles
from core.infra.worker.multi_process.process_worker import JobResult, JobStatus


def job_report_to_job_result(report: JobReport) -> JobResult:
    status = JobStatus.COMPLETED if report.success else JobStatus.FAILED
    return JobResult(
        job_id=report.job_id,
        status=status,
        result=report.data if report.success else None,
        error=report.error,
    )


def job_progress_payload(
    *,
    total_jobs: int,
    finished: int,
    completed_jobs: int,
    failed_jobs: int,
    last_job_id: str = "",
    last_job_status: str = "",
) -> Dict[str, Any]:
    """Workbench / CLI 进度回调 payload（全量累计）。"""
    pct = int(finished * 100 / total_jobs) if total_jobs else 100
    pct = min(100, max(0, pct))
    return {
        "progress_pct": pct,
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "cancelled_jobs": 0,
        "last_job_id": last_job_id,
        "last_job_status": last_job_status,
    }


def job_progress_from_run(
    progress: RunProgress,
    *,
    total_jobs: int,
    finished_offset: int = 0,
    last_job_id: str = "",
    last_job_status: str = "",
) -> Dict[str, Any]:
    """单批 JobPipeline.run 的 RunProgress + 全局 offset（MemoryAwareScheduler 多批）。"""
    finished = finished_offset + progress.finished
    return job_progress_payload(
        total_jobs=total_jobs,
        finished=finished,
        completed_jobs=progress.ok,
        failed_jobs=progress.fail,
        last_job_id=last_job_id,
        last_job_status=last_job_status,
    )


def run_stock_jobs_via_pipeline(
    *,
    stock_jobs: List[Dict[str, Any]],
    build_payload: Callable[[Dict[str, Any]], Dict[str, Any]],
    execute: Callable[[JobContext], Dict[str, Any]],
    max_workers: int,
    total_jobs: int,
    run_name: str = "jobs",
    finished_offset: int = 0,
    completed_offset: int = 0,
    failed_offset: int = 0,
    on_job_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    log_progress: bool = True,
    progress_log_label: Optional[str] = None,
    job_id_fn: Optional[Callable[[Dict[str, Any]], str]] = None,
    progress_units_from_report: Optional[
        Callable[[JobReport], Tuple[int, int, int]]
    ] = None,
    worker_profile: str = WorkerProfiles.DEFAULT,
) -> List[JobResult]:
    """
    对一批单股任务跑 JobPipeline（QUEUE + PROCESS），返回 JobResult 列表。
    """
    if not stock_jobs:
        return []

    label = progress_log_label or run_name
    resolve_job_id = job_id_fn or (lambda job: str(job.get("stock_id") or job.get("job_id")))
    pipeline_jobs = [
        Job(job_id=resolve_job_id(job), payload=build_payload(job))
        for job in stock_jobs
    ]

    results: List[JobResult] = []
    reported_ids: set[str] = set()
    progress_meta = {"last_job_id": "", "last_job_status": ""}
    log_state = {"last_pct": -1, "last_log_at": time.time(), "last_done": 0}

    def _emit_progress(*, finished: int, ok: int, fail: int) -> None:
        payload = job_progress_payload(
            total_jobs=total_jobs,
            finished=finished,
            completed_jobs=ok,
            failed_jobs=fail,
            last_job_id=progress_meta["last_job_id"],
            last_job_status=progress_meta["last_job_status"],
        )
        if on_job_progress is not None:
            on_job_progress(payload)
        if not log_progress:
            return
        pct = int(payload["progress_pct"])
        now = time.time()
        should_log = (
            finished >= total_jobs
            or finished >= log_state["last_done"] + PROGRESS_LOG_EVERY_N
            or (
                now - log_state["last_log_at"] >= PROGRESS_LOG_INTERVAL_SEC
                and finished > log_state["last_done"]
            )
            or pct >= log_state["last_pct"] + 5
        )
        if should_log:
            logger.info(
                "[%s] 进度: %s/%s (%s%%) 成功=%s 失败=%s",
                label,
                finished,
                total_jobs,
                pct,
                ok,
                fail,
            )
            log_state["last_done"] = finished
            log_state["last_log_at"] = now
            log_state["last_pct"] = pct

    stock_finished = finished_offset
    stock_ok = completed_offset
    stock_fail = failed_offset

    def on_result(report: JobReport, progress: RunProgress) -> None:
        reported_ids.add(report.job_id)
        progress_meta["last_job_id"] = report.job_id
        progress_meta["last_job_status"] = "completed" if report.success else "failed"
        results.append(job_report_to_job_result(report))
        if progress_units_from_report is not None:
            units, ok_u, fail_u = progress_units_from_report(report)
            nonlocal stock_finished, stock_ok, stock_fail
            stock_finished += units
            stock_ok += ok_u
            stock_fail += fail_u
            _emit_progress(finished=stock_finished, ok=stock_ok, fail=stock_fail)
        else:
            _emit_progress(
                finished=finished_offset + progress.finished,
                ok=completed_offset + progress.ok,
                fail=failed_offset + progress.fail,
            )

    settings = JobPipelineSettings(
        worker=ExecutionBackend.PROCESS,
        execute_mode=ExecuteMode.QUEUE,
        max_workers=max_workers,
        continue_on_failure=True,
        duckdb_process_pool_scope="auto",
        worker_profile=worker_profile,
    )
    dispatcher = JobPipeline(
        settings=settings,
        execute=execute,
        on_result=on_result,
    )
    logged_first_execute_failure = False
    dispatch = dispatcher.run(pipeline_jobs, run_name=run_name)

    if progress_units_from_report is None:
        batch_ok = dispatch.completed
        batch_fail = dispatch.failed
        _emit_progress(
            finished=finished_offset + batch_ok + batch_fail,
            ok=completed_offset + batch_ok,
            fail=failed_offset + batch_fail,
        )

    for failure in dispatch.failures:
        if failure.phase != JobFailurePhase.EXECUTE:
            continue
        if failure.job_id in reported_ids:
            continue
        if not logged_first_execute_failure:
            logged_first_execute_failure = True
            logger.warning(
                "[%s] 首个 execute 失败 job=%s: %s",
                label,
                failure.job_id,
                failure.error,
            )
        results.append(
            JobResult(
                job_id=failure.job_id,
                status=JobStatus.FAILED,
                error=failure.error,
            )
        )
        reported_ids.add(failure.job_id)

    return results
