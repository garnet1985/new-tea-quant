"""Strategy 单股 JobPipeline 公共调度（enum / price 等）。"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

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
from core.infra.worker.multi_process.process_worker import JobResult, JobStatus


def job_report_to_job_result(report: JobReport) -> JobResult:
    status = JobStatus.COMPLETED if report.success else JobStatus.FAILED
    return JobResult(
        job_id=report.job_id,
        status=status,
        result=report.data if report.success else None,
        error=report.error,
    )


def legacy_progress_from_counts(
    *,
    total_jobs: int,
    finished: int,
    completed_jobs: int,
    failed_jobs: int,
    last_job_id: str = "",
    last_job_status: str = "",
) -> Dict[str, Any]:
    """适配 Workbench / ProcessWorker 风格的 on_job_done payload（全量累计）。"""
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


def legacy_progress_from_run_progress(
    progress: RunProgress,
    *,
    total_jobs: int,
    finished_offset: int = 0,
    last_job_id: str = "",
    last_job_status: str = "",
) -> Dict[str, Any]:
    """单批 JobPipeline.run 的 RunProgress + 全局 offset（MemoryAwareScheduler 多批）。"""
    finished = finished_offset + progress.finished
    return legacy_progress_from_counts(
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
    on_legacy_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
    log_progress: bool = True,
    progress_log_label: Optional[str] = None,
) -> List[JobResult]:
    """
    对一批单股任务跑 JobPipeline（QUEUE + PROCESS），返回 JobResult 列表。
    """
    if not stock_jobs:
        return []

    label = progress_log_label or run_name
    pipeline_jobs = [
        Job(job_id=str(job["stock_id"]), payload=build_payload(job))
        for job in stock_jobs
    ]

    results: List[JobResult] = []
    reported_ids: set[str] = set()
    progress_meta = {"last_job_id": "", "last_job_status": ""}
    log_state = {"last_pct": -1, "last_log_at": time.time(), "last_done": 0}

    def _emit_progress(*, finished: int, ok: int, fail: int) -> None:
        payload = legacy_progress_from_counts(
            total_jobs=total_jobs,
            finished=finished,
            completed_jobs=ok,
            failed_jobs=fail,
            last_job_id=progress_meta["last_job_id"],
            last_job_status=progress_meta["last_job_status"],
        )
        if on_legacy_progress is not None:
            on_legacy_progress(payload)
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

    def on_result(report: JobReport, progress: RunProgress) -> None:
        reported_ids.add(report.job_id)
        progress_meta["last_job_id"] = report.job_id
        progress_meta["last_job_status"] = "completed" if report.success else "failed"
        results.append(job_report_to_job_result(report))
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
    )
    dispatcher = JobPipeline(
        settings=settings,
        execute=execute,
        on_result=on_result,
    )
    dispatch = dispatcher.run(pipeline_jobs, run_name=run_name)

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
        results.append(
            JobResult(
                job_id=failure.job_id,
                status=JobStatus.FAILED,
                error=failure.error,
            )
        )
        reported_ids.add(failure.job_id)

    return results
