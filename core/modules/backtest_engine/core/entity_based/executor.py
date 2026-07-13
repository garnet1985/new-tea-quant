"""
Backtest Engine - entity_based Executor

时间线模式执行器：QUEUE 填池 + ProcessPoolExecutor。
模块级只导出 ``EntityExecutor``；结果、Hook、子进程入口均为类成员。
"""
from __future__ import annotations

import logging
import multiprocessing as mp
import time
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from core.modules.backtest_engine.core.shared.context import ExecutionContext
from core.modules.backtest_engine.core.shared.job_lifecycle import run_job_lifecycle
from core.modules.backtest_engine.core.shared.types import (
    ExecuteFn,
    Job,
    JobContext,
    JobFailure,
    JobFailurePhase,
    ChildProcessTaskStartFn,
    ChildProcessTaskCompleteFn,
    JobReport,
    RunProgress,
)
from core.modules.backtest_engine.core.entity_based.planner import DispatchPlan, JobBatch

logger = logging.getLogger(__name__)


class EntityExecutor:
    """时间线模式执行器（QUEUE 填池 + ProcessPoolExecutor）。"""

    ExecuteFn = ExecuteFn

    class OnAfterAllTasksCompleteHook(Callable):
        """全局清理回调：接收 JobReport列表（主进程）。"""

        def __call__(self, reports: List[JobReport]) -> None:
            ...

    class OnSingleTaskResultHook(Callable):
        """单task结果回调：接收 JobReport 和 RunProgress（主进程，用于进度更新）。"""

        def __call__(self, report: JobReport, progress: RunProgress) -> None:
            ...

    @dataclass
    class ExecutionResult:
        """entity_based 执行结果。"""

        success: bool
        total_jobs: int
        completed_jobs: int
        failed_jobs: int
        failures: List[JobFailure]
        elapsed_seconds: float
        job_results: List[JobReport]

    @staticmethod
    def execute(
        plan: DispatchPlan,
        batches: List[JobBatch],
        context: ExecutionContext,
        execute_fn: ExecuteFn,
        on_child_process_task_start: Optional[ChildProcessTaskStartFn] = None,
        on_child_process_task_complete: Optional[ChildProcessTaskCompleteFn] = None,
        on_single_task_result: Optional[EntityExecutor.OnSingleTaskResultHook] = None,
        on_after_all_tasks_complete: Optional[EntityExecutor.OnAfterAllTasksCompleteHook] = None,
        log_label: str = "执行",
        admission_limit: Optional[int] = None,
        get_admission_limit: Optional[Callable[[], int]] = None,
    ) -> EntityExecutor.ExecutionResult:
        """Run batch jobs with QUEUE fill-pool (complete-one submit-one)."""
        if not batches:
            logger.info("%s无jobs需要执行", log_label)
            return EntityExecutor.ExecutionResult(
                success=True,
                total_jobs=0,
                completed_jobs=0,
                failed_jobs=0,
                failures=[],
                elapsed_seconds=0.0,
                job_results=[],
            )

        jobs = EntityExecutor._build_jobs_from_batches(batches)
        pool_workers = max(1, plan.max_workers)
        prefetch = max(0, plan.prefetch_ahead)
        default_submit_cap = admission_limit if admission_limit is not None else (
            pool_workers + prefetch
        )
        default_submit_cap = max(1, default_submit_cap)

        def resolve_submit_cap() -> int:
            if get_admission_limit is not None:
                return max(1, get_admission_limit())
            return default_submit_cap

        failures: List[JobFailure] = []
        job_results: List[JobReport] = []

        logger.info(
            "%s启动: run=%s, jobs=%s, pool_workers=%s, admission=%s, entity_per_job=%s, prefetch=%s",
            log_label,
            context.task_name,
            len(jobs),
            pool_workers,
            resolve_submit_cap(),
            plan.entities_per_job,
            prefetch,
        )

        start_time = time.monotonic()
        pending_index = 0

        try:
            with ProcessPoolExecutor(max_workers=pool_workers) as pool:
                futures: Dict[Future, Job] = {}

                while pending_index < len(jobs) or futures:
                    submit_cap = resolve_submit_cap()
                    while pending_index < len(jobs) and len(futures) < submit_cap:
                        job = jobs[pending_index]
                        pending_index += 1
                        job_context = EntityExecutor._build_job_context(job, context)
                        future = pool.submit(
                            EntityExecutor._invoke_worker,
                            execute_fn,
                            job_context,
                            on_child_process_task_start,
                            on_child_process_task_complete,
                        )
                        futures[future] = job

                    if not futures:
                        break

                    done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                    for future in done:
                        job = futures.pop(future)
                        EntityExecutor._finish_future(
                            future,
                            job,
                            context,
                            failures,
                            job_results,
                            on_single_task_result,
                            on_after_all_tasks_complete,
                            log_label,
                        )

        except KeyboardInterrupt:
            logger.info("%s收到Ctrl+C，停止执行", log_label)
            raise

        elapsed_seconds = time.monotonic() - start_time
        result = EntityExecutor.ExecutionResult(
            success=context.fail_count == 0,
            total_jobs=context.total_jobs,
            completed_jobs=context.success_count,
            failed_jobs=context.fail_count,
            failures=failures,
            elapsed_seconds=elapsed_seconds,
            job_results=job_results,
        )

        if on_after_all_tasks_complete:
            try:
                on_after_all_tasks_complete(job_results)
            except Exception as exc:
                logger.warning(
                    "%s on_after_all_tasks_complete failed: error=%s",
                    log_label,
                    exc,
                )

        logger.info(
            "%s完成: run=%s, jobs=%s, ok=%s, fail=%s, elapsed=%.2fs",
            log_label,
            context.task_name,
            context.total_jobs,
            context.success_count,
            context.fail_count,
            elapsed_seconds,
        )
        return result

    @staticmethod
    def _invoke_worker(
        execute_fn: ExecuteFn,
        job_context: JobContext,
        on_child_process_task_start: Optional[ChildProcessTaskStartFn] = None,
        on_child_process_task_complete: Optional[ChildProcessTaskCompleteFn] = None,
    ) -> Dict[str, Any]:
        """Process-pool entry: init → execute_fn → release。"""
        from core.modules.backtest_engine.core.shared.worker_data_runtime import (
            bootstrap_worker_data_manager,
        )

        bootstrap_worker_data_manager()
        rss_before_mb = EntityExecutor._process_rss_mb()
        t0 = time.perf_counter()
        try:
            raw = run_job_lifecycle(
                execute_fn,
                job_context,
                on_child_process_task_start=on_child_process_task_start,
                on_child_process_task_complete=on_child_process_task_complete,
            )
        except Exception as exc:
            wall_sec = time.perf_counter() - t0
            rss_after_mb = EntityExecutor._process_rss_mb()
            return {
                "success": False,
                "job_id": job_context.job_id,
                "error": str(exc),
                "entities_count": EntityExecutor._entities_count_from_payload(
                    job_context.payload
                ),
                "wall_sec": wall_sec,
                "peak_rss_mb": max(rss_before_mb, rss_after_mb),
            }

        wall_sec = time.perf_counter() - t0
        rss_after_mb = EntityExecutor._process_rss_mb()
        return EntityExecutor._normalize_worker_result(
            job_context,
            raw,
            wall_sec=wall_sec,
            peak_rss_mb=max(rss_before_mb, rss_after_mb),
        )

    @staticmethod
    def _finish_future(
        future: Future,
        job: Job,
        context: ExecutionContext,
        failures: List[JobFailure],
        job_results: List[JobReport],
        on_single_task_result: Optional[EntityExecutor.OnSingleTaskResultHook],
        on_after_all_tasks_complete: Optional[EntityExecutor.OnAfterAllTasksCompleteHook],
        log_label: str,
    ) -> None:
        job_context = EntityExecutor._build_job_context(job, context)
        try:
            raw_result = future.result()
            report = EntityExecutor._normalize_report(job.job_id, raw_result)
            if not report.success:
                failures.append(
                    JobFailure(
                        job_id=job.job_id,
                        phase=JobFailurePhase.EXECUTE,
                        error=report.error or "execute returned success=False",
                    )
                )
            job_results.append(report)
            context.update_progress(report.success)
            if on_single_task_result:
                on_single_task_result(
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
            context.update_progress(success=False)
            if on_single_task_result:
                on_single_task_result(
                    JobReport(job_id=job.job_id, success=False, error=str(exc)),
                    RunProgress(
                        finished=context.finished_jobs,
                        total=context.total_jobs,
                        ok=context.success_count,
                        fail=context.fail_count,
                    ),
                )

    @staticmethod
    def _build_jobs_from_batches(batches: List[JobBatch]) -> List[Job]:
        jobs: List[Job] = []
        for batch in batches:
            jobs.append(Job(job_id=batch.batch_id, payload=batch.payload))
        return jobs

    @staticmethod
    def _build_job_context(job: Job, context: ExecutionContext) -> JobContext:
        payload = dict(job.payload)
        payload["_executor"] = context.executor
        payload["_job_id"] = job.job_id
        payload["_task_name"] = context.task_name
        if context.business_data:
            payload["_business_data"] = context.business_data
        return JobContext(
            job_id=job.job_id,
            payload=payload,
            task_name=context.task_name,
        )

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
    def _entities_count_from_payload(payload: Dict[str, Any]) -> int:
        raw = payload.get("entities_count")
        if raw is None:
            raise ValueError("worker payload 须含 entities_count")
        return max(1, int(raw))

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
        if "entities_count" not in out:
            out["entities_count"] = EntityExecutor._entities_count_from_payload(
                job_context.payload
            )
        return out

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


__all__ = ["EntityExecutor"]
