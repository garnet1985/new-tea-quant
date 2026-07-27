"""data_source 私有：多 bundle 线程队列管道（THREAD + QUEUE + on_result）。

从 ``infra.job_pipeline`` 收窄迁入：只保留抓取所需的有界线程池调度。
"""
from __future__ import annotations

import logging
import multiprocessing as mp
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class JobFailurePhase(str, Enum):
    EXECUTE = "execute"
    REPORT = "report"


@dataclass(frozen=True)
class Job:
    job_id: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class JobContext:
    job_id: str
    payload: Dict[str, Any]
    run_name: str = ""


@dataclass
class JobReport:
    job_id: str
    success: bool
    data: Any = None
    error: Optional[str] = None


@dataclass
class RunProgress:
    finished: int
    total: int
    ok: int
    fail: int


@dataclass
class JobFailure:
    job_id: str
    phase: JobFailurePhase
    error: str


@dataclass
class DispatchResult:
    total: int = 0
    completed: int = 0
    failed: int = 0
    failures: List[JobFailure] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    run_name: str = ""


@dataclass
class JobPipelineSettings:
    """线程队列设置（无进程后端 / BATCH / profile）。"""

    max_workers: Union[str, int] = "auto"
    prefetch_ahead: int = 2
    continue_on_failure: bool = True
    reserve_cores: int = 1


ExecuteFn = Callable[[JobContext], Any]
OnResultHook = Callable[[JobReport, RunProgress], None]


def _resolve_max_workers(max_workers: Union[str, int], *, reserve_cores: int) -> int:
    if isinstance(max_workers, str) and max_workers.lower() == "auto":
        cpu = mp.cpu_count() or 1
        reserve = max(0, min(int(reserve_cores), cpu - 1))
        return max(1, cpu - reserve)
    return max(1, int(max_workers))


class _ThreadExecutor:
    def __init__(self, *, max_workers: int, execute: ExecuteFn) -> None:
        self._max_workers = max(1, int(max_workers))
        self._execute = execute
        self._pool: Optional[ThreadPoolExecutor] = None

    @property
    def max_workers(self) -> int:
        return self._max_workers

    def submit(self, context: JobContext) -> Future:
        if self._pool is None:
            self._pool = ThreadPoolExecutor(max_workers=self._max_workers)
        return self._pool.submit(self._execute, context)

    def shutdown(self, *, wait: bool = True) -> None:
        if self._pool is not None:
            self._pool.shutdown(wait=wait, cancel_futures=not wait)
            self._pool = None


class JobPipeline:
    """有界线程队列：完成 1 补 1；结果经 on_result 回主线程。"""

    def __init__(
        self,
        *,
        settings: JobPipelineSettings,
        execute: ExecuteFn,
        on_result: OnResultHook,
        executor: Optional[_ThreadExecutor] = None,
    ) -> None:
        self._settings = settings
        self._on_result = on_result
        workers = _resolve_max_workers(
            settings.max_workers, reserve_cores=settings.reserve_cores
        )
        self._executor = executor or _ThreadExecutor(
            max_workers=workers, execute=execute
        )
        self._pending_jobs: List[Job] = []
        self._ready_queue: List[JobContext] = []
        self._failures: List[JobFailure] = []
        self._completed = 0
        self._failed = 0
        self._total = 0
        self._cancelled = False
        self._run_name = ""

    def run(self, jobs: List[Job], *, run_name: str = "") -> DispatchResult:
        self._pending_jobs = list(jobs)
        self._ready_queue = []
        self._failures = []
        self._completed = 0
        self._failed = 0
        self._total = len(jobs)
        self._cancelled = False
        self._run_name = run_name

        start = time.monotonic()
        futures: Dict[Future, JobContext] = {}
        try:
            while not self._cancelled:
                self._prefetch(in_flight=len(futures))
                while (
                    len(futures) < self._executor.max_workers
                    and self._ready_queue
                    and not self._cancelled
                ):
                    context = self._ready_queue.pop(0)
                    futures[self._executor.submit(context)] = context

                if not futures:
                    if not self._pending_jobs and not self._ready_queue:
                        break
                    continue

                if not self._drain(futures):
                    break
        except KeyboardInterrupt:
            self._cancelled = True
            if self._run_name:
                logger.info("[%s] 收到 Ctrl+C，停止调度并回收 worker…", self._run_name)
            raise
        finally:
            self._executor.shutdown(wait=True)
            self._pending_jobs.clear()
            self._ready_queue.clear()

        return DispatchResult(
            total=self._total,
            completed=self._completed,
            failed=self._failed,
            failures=list(self._failures),
            elapsed_seconds=time.monotonic() - start,
            run_name=self._run_name,
        )

    def _ready_capacity(self) -> int:
        return self._executor.max_workers + max(0, self._settings.prefetch_ahead)

    def _prefetch(self, *, in_flight: int) -> None:
        cap = self._ready_capacity()
        while self._pending_jobs and len(self._ready_queue) + in_flight < cap:
            job = self._pending_jobs.pop(0)
            payload = dict(job.payload)
            payload.setdefault("_job_id", job.job_id)
            self._ready_queue.append(
                JobContext(job_id=job.job_id, payload=payload, run_name=self._run_name)
            )

    def _drain(self, futures: Dict[Future, JobContext]) -> bool:
        done, _ = wait(futures.keys(), return_when=FIRST_COMPLETED)
        for future in done:
            context = futures.pop(future)
            try:
                raw = future.result()
                self._on_success(context, raw)
            except Exception as exc:
                self._on_failure(context, str(exc))
            if not self._settings.continue_on_failure and self._failed > 0:
                self._cancelled = True
                return False
        return True

    def _on_success(self, context: JobContext, raw: object) -> None:
        report = self._normalize(context, raw)
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
            self._on_result(
                report,
                RunProgress(
                    finished=self._completed + self._failed,
                    total=self._total,
                    ok=self._completed,
                    fail=self._failed,
                ),
            )
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

    def _on_failure(self, context: JobContext, error: str) -> None:
        self._failed += 1
        self._failures.append(
            JobFailure(
                job_id=context.job_id,
                phase=JobFailurePhase.EXECUTE,
                error=error,
            )
        )

    @staticmethod
    def _normalize(context: JobContext, raw: object) -> JobReport:
        if isinstance(raw, JobReport):
            return raw
        if isinstance(raw, dict):
            success = bool(raw.get("success", True))
            return JobReport(
                job_id=context.job_id,
                success=success,
                data=raw,
                error=raw.get("error") if not success else None,
            )
        return JobReport(job_id=context.job_id, success=True, data=raw)


__all__ = [
    "DispatchResult",
    "Job",
    "JobContext",
    "JobFailure",
    "JobFailurePhase",
    "JobPipeline",
    "JobPipelineSettings",
    "JobReport",
    "RunProgress",
]
