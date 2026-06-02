"""
JobDispatcher - 任务装填、分发与结果回收。

与 infra.worker 平级组合：
- JobExecutor：多进程 / 多线程并行 execute
- JobDispatcher：pending shells、on_stage_job、有界 ready 队列、自动填池、on_report

不兼容旧 ProcessWorker 队列 pipeline；业务方后续改为 JobDispatcher.run(shells)。
"""
from __future__ import annotations

import logging
import time
from concurrent.futures import FIRST_COMPLETED, Future, wait
from typing import Dict, List, Optional

from core.infra.job_dispatcher.executor import JobExecutor
from core.infra.job_dispatcher.hooks import OnReleaseStagedHook, OnReportHook, OnStageJobHook
from core.infra.job_dispatcher.types import (
    DispatchConfig,
    DispatchResult,
    JobFailure,
    JobFailurePhase,
    JobReport,
    JobShell,
    StagedJob,
)

logger = logging.getLogger(__name__)


class JobDispatcher:
    """
    任务调度器：装填 → 提交 JobExecutor → 回收报告。

    Hooks:
        on_stage_job(shell) -> StagedJob
        on_report(JobReport)
        on_release_staged(StagedJob)  # 可选
    """

    def __init__(
        self,
        *,
        on_stage_job: OnStageJobHook,
        on_report: OnReportHook,
        executor: JobExecutor,
        config: Optional[DispatchConfig] = None,
        on_release_staged: Optional[OnReleaseStagedHook] = None,
    ) -> None:
        self._on_stage_job = on_stage_job
        self._on_report = on_report
        self._executor = executor
        self._on_release_staged = on_release_staged
        self._config = config or DispatchConfig()

        self._pending_shells: List[JobShell] = []
        self._ready_queue: List[StagedJob] = []
        self._failures: List[JobFailure] = []
        self._completed = 0
        self._failed = 0
        self._total = 0
        self._cancelled = False

    @property
    def config(self) -> DispatchConfig:
        return self._config

    @property
    def executor(self) -> JobExecutor:
        return self._executor

    def run(self, shells: List[JobShell]) -> DispatchResult:
        """消费 shell 列表，完成装填、并行执行与报告回收。"""
        self._reset_run_state(shells)
        start = time.monotonic()
        futures: Dict[Future, StagedJob] = {}

        try:
            while not self._cancelled:
                self._prefetch_until_ready(in_flight_count=len(futures))

                while (
                    len(futures) < self._executor.max_workers
                    and self._ready_queue
                    and not self._cancelled
                ):
                    staged = self._ready_queue.pop(0)
                    future = self._executor.submit(staged.job_id, staged.payload)
                    futures[future] = staged

                if not futures:
                    if not self._pending_shells and not self._ready_queue:
                        break
                    continue

                done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
                for future in done:
                    staged = futures.pop(future)
                    try:
                        raw = future.result()
                        self._handle_worker_success(staged, raw)
                    except Exception as exc:
                        self._handle_worker_failure(staged, str(exc))
                    finally:
                        self._release_staged(staged)
        finally:
            self._executor.shutdown(wait=True)
            self._cleanup_run()

        return self._build_dispatch_result(time.monotonic() - start)

    def cancel(self) -> None:
        self._cancelled = True

    def _reset_run_state(self, shells: List[JobShell]) -> None:
        self._pending_shells = list(shells)
        self._ready_queue = []
        self._failures = []
        self._completed = 0
        self._failed = 0
        self._total = len(shells)
        self._cancelled = False

    def _ready_queue_capacity(self) -> int:
        if self._config.ready_queue_limit is not None:
            return max(1, self._config.ready_queue_limit)
        return self._executor.max_workers + max(0, self._config.prefetch_ahead)

    def _prefetch_until_ready(self, *, in_flight_count: int) -> None:
        cap = self._ready_queue_capacity()
        while self._pending_shells and len(self._ready_queue) + in_flight_count < cap:
            shell = self._pending_shells.pop(0)
            staged = self._stage_shell(shell)
            if staged is not None:
                self._ready_queue.append(staged)

    def _stage_shell(self, shell: JobShell) -> Optional[StagedJob]:
        try:
            return self._on_stage_job(shell)
        except Exception as exc:
            logger.exception("on_stage_job failed: job_id=%s", shell.job_id)
            self._record_failure(
                JobFailure(
                    job_id=shell.job_id,
                    phase=JobFailurePhase.STAGE,
                    error=str(exc),
                )
            )
            return None

    def _handle_worker_success(self, staged: StagedJob, raw_result: object) -> None:
        report = self._normalize_report(staged, raw_result)
        try:
            self._emit_report(report)
            if report.success:
                self._completed += 1
            else:
                self._failed += 1
                self._record_failure(
                    JobFailure(
                        job_id=staged.job_id,
                        phase=JobFailurePhase.EXECUTE,
                        error=report.error or "execute returned success=False",
                    )
                )
        except Exception as exc:
            logger.exception("on_report failed: job_id=%s", staged.job_id)
            self._failed += 1
            self._record_failure(
                JobFailure(
                    job_id=staged.job_id,
                    phase=JobFailurePhase.REPORT,
                    error=str(exc),
                )
            )

    def _handle_worker_failure(self, staged: StagedJob, error: str) -> None:
        self._failed += 1
        self._record_failure(
            JobFailure(
                job_id=staged.job_id,
                phase=JobFailurePhase.EXECUTE,
                error=error,
            )
        )

    def _emit_report(self, report: JobReport) -> None:
        self._on_report(report)

    def _release_staged(self, staged: StagedJob) -> None:
        if self._on_release_staged is not None:
            try:
                self._on_release_staged(staged)
            except Exception:
                logger.exception("on_release_staged failed: job_id=%s", staged.job_id)

    def _build_dispatch_result(self, elapsed_seconds: float) -> DispatchResult:
        return DispatchResult(
            total=self._total,
            completed=self._completed,
            failed=self._failed,
            failures=list(self._failures),
            elapsed_seconds=elapsed_seconds,
        )

    def _cleanup_run(self) -> None:
        self._pending_shells.clear()
        self._ready_queue.clear()

    def _record_failure(self, failure: JobFailure) -> None:
        self._failures.append(failure)

    @staticmethod
    def _normalize_report(staged: StagedJob, raw_result: object) -> JobReport:
        if isinstance(raw_result, JobReport):
            return raw_result
        if isinstance(raw_result, dict):
            success = bool(raw_result.get("success", True))
            return JobReport(
                job_id=staged.job_id,
                success=success,
                data=raw_result,
                error=raw_result.get("error") if not success else None,
            )
        return JobReport(job_id=staged.job_id, success=True, data=raw_result)
