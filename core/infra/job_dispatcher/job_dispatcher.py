"""
JobDispatcher - 任务装填、分发与结果回收。

jobs[] → [to_executable_job?] → executor.execute(payload) → on_result
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import FIRST_COMPLETED, Future, wait
from typing import Dict, List, Optional

from core.infra.job_dispatcher.executor import JobExecutor, create_job_executor
from core.infra.job_dispatcher.hooks import (
    ExecuteFn,
    OnReleaseHook,
    OnResultHook,
    ToExecutableJobHook,
)
from core.infra.job_dispatcher.settings import JobDispatchSettings
from core.infra.job_dispatcher.types import (
    DispatchResult,
    ExecuteMode,
    Job,
    JobFailure,
    JobFailurePhase,
    JobReport,
    PreparedJob,
    RunProgress,
)

logger = logging.getLogger(__name__)


class JobDispatcher:
    """
    任务调度器：可选 prepare → 提交 JobExecutor → on_result。

    Hooks:
        to_executable_job(job) -> Job   # 可选；None 时 payload 直送 execute
        on_result(report, progress)
        on_release(prepared)            # 可选 cleanup
    """

    def __init__(
        self,
        *,
        settings: JobDispatchSettings,
        execute: ExecuteFn,
        on_result: OnResultHook,
        to_executable_job: Optional[ToExecutableJobHook] = None,
        on_release: Optional[OnReleaseHook] = None,
        executor: Optional[JobExecutor] = None,
    ) -> None:
        self._settings = settings
        self._execute = execute
        self._to_executable_job = to_executable_job
        self._on_result = on_result
        self._on_release = on_release
        self._executor = executor or create_job_executor(settings, execute=execute)

        self._pending_jobs: List[Job] = []
        self._ready_queue: List[PreparedJob] = []
        self._failures: List[JobFailure] = []
        self._completed = 0
        self._failed = 0
        self._total = 0
        self._cancelled = False
        self._run_name = ""

    @property
    def settings(self) -> JobDispatchSettings:
        return self._settings

    @property
    def executor(self) -> JobExecutor:
        return self._executor

    def run(self, jobs: List[Job], *, run_name: str = "") -> DispatchResult:
        """消费 job 列表，完成 prepare、并行执行与结果回收。"""
        mode = self._settings.execute_mode
        if mode == ExecuteMode.ELASTIC:
            raise NotImplementedError("ExecuteMode.ELASTIC is not implemented yet")
        if mode == ExecuteMode.BATCH:
            return self._run_batch(jobs, run_name=run_name)
        return self._run_queue(jobs, run_name=run_name)

    def cancel(self) -> None:
        self._cancelled = True

    def _run_queue(self, jobs: List[Job], *, run_name: str) -> DispatchResult:
        self._reset_run_state(jobs, run_name)
        start = time.monotonic()
        futures: Dict[Future, PreparedJob] = {}

        try:
            while not self._cancelled:
                self._prefetch_until_ready(in_flight_count=len(futures))

                while (
                    len(futures) < self._executor.max_workers
                    and self._ready_queue
                    and not self._cancelled
                ):
                    prepared = self._ready_queue.pop(0)
                    future = self._executor.submit(prepared.job_id, prepared.payload)
                    futures[future] = prepared

                if not futures:
                    if not self._pending_jobs and not self._ready_queue:
                        break
                    continue

                done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                for future in done:
                    prepared = futures.pop(future)
                    try:
                        raw = future.result()
                        self._handle_worker_success(prepared, raw)
                    except Exception as exc:
                        self._handle_worker_failure(prepared, str(exc))
                    finally:
                        self._release_prepared(prepared)
                    if not self._settings.continue_on_failure and self._failed > 0:
                        self._cancelled = True
                        break
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
                prepared_batch: List[PreparedJob] = []
                for job in batch:
                    prepared = self._prepare_job(job)
                    if prepared is not None:
                        prepared_batch.append(prepared)

                futures: Dict[Future, PreparedJob] = {}
                pending_submit = list(prepared_batch)

                while pending_submit or futures:
                    if self._cancelled:
                        break
                    while (
                        pending_submit
                        and len(futures) < self._executor.max_workers
                        and not self._cancelled
                    ):
                        prepared = pending_submit.pop(0)
                        future = self._executor.submit(prepared.job_id, prepared.payload)
                        futures[future] = prepared

                    if not futures:
                        break

                    done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                    for future in done:
                        prepared = futures.pop(future)
                        try:
                            raw = future.result()
                            self._handle_worker_success(prepared, raw)
                        except Exception as exc:
                            self._handle_worker_failure(prepared, str(exc))
                        finally:
                            self._release_prepared(prepared)
                        if not self._settings.continue_on_failure and self._failed > 0:
                            self._cancelled = True
                            break
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

    def _prefetch_until_ready(self, *, in_flight_count: int) -> None:
        cap = self._ready_queue_capacity()
        while self._pending_jobs and len(self._ready_queue) + in_flight_count < cap:
            job = self._pending_jobs.pop(0)
            prepared = self._prepare_job(job)
            if prepared is not None:
                self._ready_queue.append(prepared)

    def _prepare_job(self, job: Job) -> Optional[PreparedJob]:
        try:
            if self._to_executable_job is None:
                return PreparedJob(job_id=job.job_id, payload=dict(job.payload), source=job)
            enriched = self._to_executable_job(job)
            return PreparedJob(
                job_id=enriched.job_id,
                payload=dict(enriched.payload),
                source=enriched,
            )
        except Exception as exc:
            logger.exception(
                "[%s] to_executable_job failed: job_id=%s",
                self._run_name or "-",
                job.job_id,
            )
            self._failed += 1
            self._failures.append(
                JobFailure(
                    job_id=job.job_id,
                    phase=JobFailurePhase.TO_EXECUTABLE,
                    error=str(exc),
                )
            )
            return None

    def _handle_worker_success(self, prepared: PreparedJob, raw_result: object) -> None:
        report = self._normalize_report(prepared, raw_result)
        try:
            if report.success:
                self._completed += 1
            else:
                self._failed += 1
                self._failures.append(
                    JobFailure(
                        job_id=prepared.job_id,
                        phase=JobFailurePhase.EXECUTE,
                        error=report.error or "execute returned success=False",
                    )
                )
            self._emit_result(report)
        except Exception as exc:
            logger.exception(
                "[%s] on_result failed: job_id=%s",
                self._run_name or "-",
                prepared.job_id,
            )
            self._failed += 1
            self._failures.append(
                JobFailure(
                    job_id=prepared.job_id,
                    phase=JobFailurePhase.REPORT,
                    error=str(exc),
                )
            )

    def _handle_worker_failure(self, prepared: PreparedJob, error: str) -> None:
        self._failed += 1
        self._failures.append(
            JobFailure(
                job_id=prepared.job_id,
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

    def _release_prepared(self, prepared: PreparedJob) -> None:
        if self._on_release is None:
            return
        try:
            self._on_release(prepared)
        except Exception:
            logger.exception(
                "[%s] on_release failed: job_id=%s",
                self._run_name or "-",
                prepared.job_id,
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
    def _normalize_report(prepared: PreparedJob, raw_result: object) -> JobReport:
        if isinstance(raw_result, JobReport):
            return raw_result
        if isinstance(raw_result, dict):
            success = bool(raw_result.get("success", True))
            return JobReport(
                job_id=prepared.job_id,
                success=success,
                data=raw_result,
                error=raw_result.get("error") if not success else None,
            )
        return JobReport(job_id=prepared.job_id, success=True, data=raw_result)
