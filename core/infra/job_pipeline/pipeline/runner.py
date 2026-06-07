"""JobPipeline：并行 Job 执行管道（线程/进程池 + on_result 回收）。"""
from __future__ import annotations

import logging
import time
from concurrent.futures import FIRST_COMPLETED, Future, wait
from contextlib import nullcontext
from typing import Dict, List, Optional

from core.infra.db.engines.duckdb.process_pool_scope import maybe_duckdb_worker_pool_scope
from core.infra.job_pipeline.pipeline.hooks import ExecuteFn, OnReleaseHook, OnResultHook
from core.infra.job_pipeline.pipeline.settings import JobPipelineSettings
from core.infra.job_pipeline.runtime.executor import JobExecutor, create_job_executor
from core.infra.job_pipeline.types import (
    DispatchResult,
    ExecuteMode,
    ExecutionBackend,
    Job,
    JobContext,
    JobFailure,
    JobFailurePhase,
    JobReport,
    RunProgress,
)

logger = logging.getLogger(__name__)


class JobPipeline:
    def __init__(
        self,
        *,
        settings: JobPipelineSettings,
        execute: ExecuteFn,
        on_result: OnResultHook,
        on_release: Optional[OnReleaseHook] = None,
        executor: Optional[JobExecutor] = None,
    ) -> None:
        self._settings = settings
        self._on_result = on_result
        self._on_release = on_release
        self._executor = executor or create_job_executor(settings, execute=execute)

        self._pending_jobs: List[Job] = []
        self._ready_queue: List[JobContext] = []
        self._failures: List[JobFailure] = []
        self._completed = 0
        self._failed = 0
        self._total = 0
        self._cancelled = False
        self._run_name = ""

    @property
    def settings(self) -> JobPipelineSettings:
        return self._settings

    @property
    def executor(self) -> JobExecutor:
        return self._executor

    def run(self, jobs: List[Job], *, run_name: str = "") -> DispatchResult:
        mode = self._settings.execute_mode
        if mode == ExecuteMode.ELASTIC:
            raise NotImplementedError("ExecuteMode.ELASTIC is not implemented yet")
        use_process = self._settings.worker == ExecutionBackend.PROCESS
        scope_ctx = (
            maybe_duckdb_worker_pool_scope(
                mode=self._settings.duckdb_process_pool_scope,
                use_process_pool=use_process,
                data_mgr=self._settings.duckdb_data_mgr,
                resume_main_after=self._settings.duckdb_resume_main_after_pool,
            )
            if use_process
            else nullcontext()
        )
        with scope_ctx:
            if mode == ExecuteMode.BATCH:
                return self._run_batch(jobs, run_name=run_name)
            return self._run_queue(jobs, run_name=run_name)

    def cancel(self) -> None:
        self._cancelled = True

    def _run_queue(self, jobs: List[Job], *, run_name: str) -> DispatchResult:
        self._reset_run_state(jobs, run_name)
        start = time.monotonic()
        futures: Dict[Future, JobContext] = {}

        try:
            while not self._cancelled:
                self._prefetch_until_ready(in_flight_count=len(futures))

                while (
                    len(futures) < self._executor.max_workers
                    and self._ready_queue
                    and not self._cancelled
                ):
                    context = self._ready_queue.pop(0)
                    future = self._executor.submit(context)
                    futures[future] = context

                if not futures:
                    if not self._pending_jobs and not self._ready_queue:
                        break
                    continue

                if not self._drain_completed_futures(futures):
                    break
        except KeyboardInterrupt:
            self._cancelled = True
            if self._run_name:
                logger.info("[%s] 收到 Ctrl+C，停止调度并回收 worker…", self._run_name)
            raise
        finally:
            self._executor.shutdown(wait=True)
            self._cleanup_run()

        return self._build_dispatch_result(time.monotonic() - start)

    def _run_batch(self, jobs: List[Job], *, run_name: str) -> DispatchResult:
        self._reset_run_state(jobs, run_name)
        start = time.monotonic()
        batch_size = max(1, self._settings.batch_size)

        try:
            offset = 0
            while offset < len(jobs) and not self._cancelled:
                batch = jobs[offset : offset + batch_size]
                offset += batch_size
                batch_contexts = [self._build_context(job) for job in batch]

                futures: Dict[Future, JobContext] = {}
                pending_submit = list(batch_contexts)

                while pending_submit or futures:
                    if self._cancelled:
                        break
                    while (
                        pending_submit
                        and len(futures) < self._executor.max_workers
                        and not self._cancelled
                    ):
                        context = pending_submit.pop(0)
                        future = self._executor.submit(context)
                        futures[future] = context

                    if not futures:
                        break

                    if not self._drain_completed_futures(futures):
                        break
        except KeyboardInterrupt:
            self._cancelled = True
            if self._run_name:
                logger.info("[%s] 收到 Ctrl+C，停止调度并回收 worker…", self._run_name)
            raise
        finally:
            self._executor.shutdown(wait=True)
            self._cleanup_run()

        return self._build_dispatch_result(time.monotonic() - start)

    def _reset_run_state(self, jobs: List[Job], run_name: str) -> None:
        self._pending_jobs = list(jobs)
        self._ready_queue = []
        self._failures = []
        self._completed = 0
        self._failed = 0
        self._total = len(jobs)
        self._cancelled = False
        self._run_name = run_name

    def _ready_queue_capacity(self) -> int:
        if self._settings.ready_queue_limit is not None:
            return max(1, self._settings.ready_queue_limit)
        return self._executor.max_workers + max(0, self._settings.prefetch_ahead)

    def _drain_completed_futures(self, futures: Dict[Future, JobContext]) -> bool:
        if not futures:
            return True
        done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
        for future in done:
            context = futures.pop(future)
            try:
                raw = future.result()
                self._handle_worker_success(context, raw)
            except Exception as exc:
                self._handle_worker_failure(context, str(exc))
            finally:
                self._release_context(context)
            if not self._settings.continue_on_failure and self._failed > 0:
                self._cancelled = True
                return False
        return True

    def _prefetch_until_ready(self, *, in_flight_count: int) -> None:
        cap = self._ready_queue_capacity()
        while self._pending_jobs and len(self._ready_queue) + in_flight_count < cap:
            job = self._pending_jobs.pop(0)
            self._ready_queue.append(self._build_context(job))

    def _build_context(self, job: Job) -> JobContext:
        payload = dict(job.payload)
        payload.setdefault("_job_id", job.job_id)
        return JobContext(
            job_id=job.job_id,
            payload=payload,
            run_name=self._run_name,
        )

    def _handle_worker_success(self, context: JobContext, raw_result: object) -> None:
        report = self._normalize_report(context, raw_result)
        try:
            if report.success:
                self._completed += 1
            else:
                self._failed += 1
                self._failures.append(
                    JobFailure(
                        job_id=context.job_id,
                        phase=JobFailurePhase.EXECUTE,
                        error=report.error or "execute returned success=False",
                    )
                )
            self._emit_result(report)
        except Exception as exc:
            logger.exception(
                "[%s] on_result failed: job_id=%s",
                self._run_name or "-",
                context.job_id,
            )
            self._failed += 1
            self._failures.append(
                JobFailure(
                    job_id=context.job_id,
                    phase=JobFailurePhase.REPORT,
                    error=str(exc),
                )
            )

    def _handle_worker_failure(self, context: JobContext, error: str) -> None:
        self._failed += 1
        self._failures.append(
            JobFailure(
                job_id=context.job_id,
                phase=JobFailurePhase.EXECUTE,
                error=error,
            )
        )

    def _emit_result(self, report: JobReport) -> None:
        progress = RunProgress(
            finished=self._completed + self._failed,
            total=self._total,
            ok=self._completed,
            fail=self._failed,
        )
        self._on_result(report, progress)

    def _release_context(self, context: JobContext) -> None:
        if self._on_release is None:
            return
        try:
            self._on_release(context)
        except Exception:
            logger.exception(
                "[%s] on_release failed: job_id=%s",
                self._run_name or "-",
                context.job_id,
            )

    def _build_dispatch_result(self, elapsed_seconds: float) -> DispatchResult:
        return DispatchResult(
            total=self._total,
            completed=self._completed,
            failed=self._failed,
            failures=list(self._failures),
            elapsed_seconds=elapsed_seconds,
            run_name=self._run_name,
        )

    def _cleanup_run(self) -> None:
        self._pending_jobs.clear()
        self._ready_queue.clear()

    @staticmethod
    def _normalize_report(context: JobContext, raw_result: object) -> JobReport:
        if isinstance(raw_result, JobReport):
            return raw_result
        if isinstance(raw_result, dict):
            success = bool(raw_result.get("success", True))
            return JobReport(
                job_id=context.job_id,
                success=success,
                data=raw_result,
                error=raw_result.get("error") if not success else None,
            )
        return JobReport(job_id=context.job_id, success=True, data=raw_result)
