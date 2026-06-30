"""
Backtest Engine - Slice-based Executor

Calendar-slice execution: plan embedded in payload, orchestrator runs in-process.

The orchestrator spawns Reader/Compute child processes itself; wrapping it in
ProcessPoolExecutor would run inside a daemon worker, which cannot fork again
("daemonic processes are not allowed to have children").
"""
from __future__ import annotations

import logging
import multiprocessing as mp
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from core.modules.backtest_engine.core.shared.context import ExecutionContext
from core.modules.backtest_engine.core.shared.progress import RunProgressReporter
from core.modules.backtest_engine.core.shared.types import (
    ExecuteFn,
    Job,
    JobContext,
    JobFailure,
    JobFailurePhase,
    JobReport,
    RunProgress,
)
from core.modules.backtest_engine.core.slice_based.planner import (
    SliceDispatchPlan,
    SliceJobBatch,
)

logger = logging.getLogger(__name__)


class SliceExecutor:
    """Calendar-slice executor (bulk job + injected orchestrator execute_fn)."""

    ExecuteFn = ExecuteFn

    class OnResultHook(Callable):
        """Result callback: receives JobReport and RunProgress."""

        def __call__(self, report: JobReport, progress: RunProgress) -> None:
            ...

    @dataclass
    class ExecutionResult:
        """Slice execution summary (aligned with timeline job counters)."""

        success: bool
        total_jobs: int
        completed_jobs: int
        failed_jobs: int
        failures: List[JobFailure]
        elapsed_seconds: float
        job_results: List[JobReport]

    @staticmethod
    def execute(
        plan: SliceDispatchPlan,
        batches: List[SliceJobBatch],
        context: ExecutionContext,
        execute_fn: ExecuteFn,
        on_result: Optional[SliceExecutor.OnResultHook] = None,
        log_label: str = "切片执行",
        progress_reporter: Optional[RunProgressReporter] = None,
    ) -> SliceExecutor.ExecutionResult:
        """Run calendar-slice orchestrator in the current (non-daemon) process."""
        if not batches:
            logger.info("%s无jobs需要执行", log_label)
            return SliceExecutor.ExecutionResult(
                success=True,
                total_jobs=0,
                completed_jobs=0,
                failed_jobs=0,
                failures=[],
                elapsed_seconds=0.0,
                job_results=[],
            )

        jobs = SliceExecutor._build_jobs_from_batches(batches)
        failures: List[JobFailure] = []
        job_results: List[JobReport] = []

        logger.info(
            "%s启动: run=%s, jobs=%s, reader=%s, queue=%s, slice_days=%s, slices=%s",
            log_label,
            context.task_name,
            len(jobs),
            plan.reader_workers,
            plan.queue_capacity,
            plan.slice_open_days,
            plan.dispatch_jobs,
        )

        start_time = time.monotonic()
        completed_jobs = 0
        failed_jobs = 0

        try:
            for job in jobs:
                job_context = SliceExecutor._build_job_context(
                    job,
                    context,
                    plan,
                    progress_reporter=progress_reporter,
                )
                try:
                    raw_result = SliceExecutor._invoke_worker(execute_fn, job_context)
                    report = SliceExecutor._normalize_report(job.job_id, raw_result)
                    if not report.success:
                        failures.append(
                            JobFailure(
                                job_id=job.job_id,
                                phase=JobFailurePhase.EXECUTE,
                                error=report.error or "execute returned success=False",
                            )
                        )
                        failed_jobs += 1
                    else:
                        completed_jobs += 1
                    job_results.append(report)
                    context.update_progress(report.success)
                    if on_result:
                        on_result(
                            report,
                            RunProgress(
                                finished=context.finished_jobs,
                                total=context.total_jobs,
                                ok=context.success_count,
                                fail=context.fail_count,
                            ),
                        )
                except Exception as exc:
                    failures.append(
                        JobFailure(
                            job_id=job.job_id,
                            phase=JobFailurePhase.EXECUTE,
                            error=str(exc),
                        )
                    )
                    failed_jobs += 1
                    context.update_progress(success=False)
                    if on_result:
                        on_result(
                            JobReport(
                                job_id=job.job_id,
                                success=False,
                                error=str(exc),
                            ),
                            RunProgress(
                                finished=context.finished_jobs,
                                total=context.total_jobs,
                                ok=context.success_count,
                                fail=context.fail_count,
                            ),
                        )
        except KeyboardInterrupt:
            logger.warning("%s收到Ctrl+C，停止执行", log_label)
            return SliceExecutor.ExecutionResult(
                success=False,
                total_jobs=len(jobs),
                completed_jobs=completed_jobs,
                failed_jobs=failed_jobs,
                failures=failures,
                elapsed_seconds=time.monotonic() - start_time,
                job_results=job_results,
            )

        elapsed_seconds = time.monotonic() - start_time
        success = failed_jobs == 0
        logger.info(
            "%s完成: run=%s, jobs=%s, ok=%s, fail=%s, elapsed=%.2fs",
            log_label,
            context.task_name,
            len(jobs),
            completed_jobs,
            failed_jobs,
            elapsed_seconds,
        )
        return SliceExecutor.ExecutionResult(
            success=success,
            total_jobs=len(jobs),
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            failures=failures,
            elapsed_seconds=elapsed_seconds,
            job_results=job_results,
        )

    @staticmethod
    def _invoke_worker(
        execute_fn: ExecuteFn,
        job_context: JobContext,
    ) -> Dict[str, Any]:
        """Process-pool entry: run caller execute_fn and attach metrics."""
        if mp.current_process().name != "MainProcess":
            try:
                from core.infra.db import DatabaseManager

                DatabaseManager.reset_default()
            except Exception:
                pass

        rss_before_mb = SliceExecutor._process_rss_mb()
        t0 = time.perf_counter()
        try:
            raw = execute_fn(job_context)
        except Exception as exc:
            wall_sec = time.perf_counter() - t0
            rss_after_mb = SliceExecutor._process_rss_mb()
            return {
                "success": False,
                "job_id": job_context.job_id,
                "error": str(exc),
                "slices_count": SliceExecutor._slices_count_from_payload(
                    job_context.payload
                ),
                "wall_sec": wall_sec,
                "peak_rss_mb": max(rss_before_mb, rss_after_mb),
            }

        wall_sec = time.perf_counter() - t0
        rss_after_mb = SliceExecutor._process_rss_mb()
        return SliceExecutor._normalize_worker_result(
            job_context,
            raw,
            wall_sec=wall_sec,
            peak_rss_mb=max(rss_before_mb, rss_after_mb),
        )

    @staticmethod
    def _build_jobs_from_batches(batches: List[SliceJobBatch]) -> List[Job]:
        jobs: List[Job] = []
        for batch in batches:
            jobs.append(Job(job_id=batch.batch_id, payload=batch.payload))
        return jobs

    @staticmethod
    def _build_job_context(
        job: Job,
        context: ExecutionContext,
        plan: SliceDispatchPlan,
        *,
        progress_reporter: Optional[RunProgressReporter] = None,
    ) -> JobContext:
        payload = dict(job.payload)
        payload["_executor"] = context.executor
        payload["_job_id"] = job.job_id
        payload["_task_name"] = context.task_name
        payload["_slice_plan"] = SliceExecutor._plan_to_dict(plan)
        if progress_reporter is not None:
            payload["_engine_on_execute_unit_done"] = progress_reporter.make_execute_unit_hook()
        if context.business_data:
            payload["_business_data"] = context.business_data
        return JobContext(
            job_id=job.job_id,
            payload=payload,
            task_name=context.task_name,
        )

    @staticmethod
    def _plan_to_dict(plan: SliceDispatchPlan) -> Dict[str, Any]:
        return {
            "reader_workers": plan.reader_workers,
            "reader_memory_budget_mb": plan.reader_memory_budget_mb,
            "compute_processes": plan.compute_processes,
            "compute_memory_budget_mb": plan.compute_memory_budget_mb,
            "queue_capacity": plan.queue_capacity,
            "preload_depth": plan.preload_depth,
            "slice_open_days": plan.slice_open_days,
            "dispatch_jobs": plan.dispatch_jobs,
            "memory_budget_mb": plan.memory_budget_mb,
            "oom_adjusted": plan.oom_adjusted,
        }

    @staticmethod
    def _normalize_report(job_id: str, raw_result: object) -> JobReport:
        if isinstance(raw_result, JobReport):
            return raw_result
        if isinstance(raw_result, dict):
            success = bool(raw_result.get("success", True))
            return JobReport(
                job_id=job_id,
                success=success,
                data=raw_result,
                error=raw_result.get("error") if not success else None,
            )
        return JobReport(job_id=job_id, success=True, data=raw_result)

    @staticmethod
    def _normalize_worker_result(
        job_context: JobContext,
        raw: Any,
        *,
        wall_sec: float,
        peak_rss_mb: float,
    ) -> Dict[str, Any]:
        if isinstance(raw, JobReport):
            data = raw.data if isinstance(raw.data, dict) else {"data": raw.data}
            out = dict(data)
            out.setdefault("success", raw.success)
            out.setdefault("job_id", raw.job_id)
            if raw.error:
                out.setdefault("error", raw.error)
        elif isinstance(raw, dict):
            out = dict(raw)
            out.setdefault("success", True)
            out.setdefault("job_id", job_context.job_id)
        else:
            out = {
                "success": True,
                "job_id": job_context.job_id,
                "data": raw,
            }

        out.setdefault("wall_sec", wall_sec)
        out.setdefault("peak_rss_mb", peak_rss_mb)
        if "slices_count" not in out:
            out["slices_count"] = SliceExecutor._slices_count_from_payload(
                job_context.payload
            )
        return out

    @staticmethod
    def _slices_count_from_payload(payload: Dict[str, Any]) -> int:
        plan = payload.get("_slice_plan")
        if isinstance(plan, dict) and plan.get("dispatch_jobs") is not None:
            return int(plan["dispatch_jobs"])
        return int(payload.get("slices_count") or 1)

    @staticmethod
    def _process_rss_mb() -> float:
        try:
            import os

            import psutil

            return float(psutil.Process(os.getpid()).memory_info().rss) / (
                1024.0 * 1024.0
            )
        except Exception:
            return 0.0


__all__ = ["SliceExecutor"]
