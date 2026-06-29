"""
Backtest Scheduler - General Executor

JobExecutor协议与工厂（ProcessPoolExecutor/ThreadPoolExecutor），不包含DB特殊逻辑。
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .job_pipeline import ExecuteFn
from .settings import JobPipelineSettings
from .types import ExecutionBackend, JobContext


@runtime_checkable
class JobExecutor(Protocol):
    """JobExecutor协议。"""

    @property
    def max_workers(self) -> int:
        ...

    @property
    def requires_picklable_payload(self) -> bool:
        ...

    def submit(self, context: JobContext) -> Any:
        ...

    def shutdown(self, *, wait: bool = True, timeout: float | None = None) -> None:
        ...

    def get_stats(self) -> dict[str, Any]:
        ...


def create_job_executor(settings: JobPipelineSettings, *, execute: ExecuteFn) -> JobExecutor:
    """创建JobExecutor（General逻辑，不包含DB特殊处理）。"""
    # TODO: Phase 2.5需要迁移resolve_pipeline_workers
    # 暂时使用简化逻辑
    if settings.max_workers in (None, "", "auto"):
        # 简化：使用默认值4（后续迁移WorkerProbe）
        resolved = 4
    else:
        resolved = max(1, int(settings.max_workers))
    if settings.worker == ExecutionBackend.PROCESS:
        return ProcessJobExecutor(
            max_workers=resolved,
            execute=execute,
            start_method=settings.start_method,
        )
    if settings.worker == ExecutionBackend.THREAD:
        return ThreadJobExecutor(max_workers=resolved, execute=execute)
    raise ValueError(f"Unsupported ExecutionBackend: {settings.worker!r}")


# ProcessPoolExecutor/ThreadPoolExecutor实现（从pool.py迁移）
import multiprocessing as mp
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor


class ProcessJobExecutor:
    """ProcessPoolExecutor实现。"""

    def __init__(
        self,
        *,
        max_workers: int,
        execute: ExecuteFn,
        start_method: str = "spawn",
        timeout: float | None = None,
    ) -> None:
        self._max_workers = max(1, int(max_workers))
        self._execute = execute
        self._start_method = start_method
        self._timeout = timeout
        self._pool: ProcessPoolExecutor | None = None
        self._submitted = 0

    @property
    def max_workers(self) -> int:
        return self._max_workers

    @property
    def requires_picklable_payload(self) -> bool:
        return True

    def _ensure_pool(self) -> ProcessPoolExecutor:
        if self._pool is None:
            ctx = mp.get_context(self._start_method)
            self._pool = ProcessPoolExecutor(
                max_workers=self._max_workers,
                mp_context=ctx,
            )
        return self._pool

    def submit(self, context: JobContext) -> Future:
        self._submitted += 1
        pool = self._ensure_pool()
        # TODO: Phase 2.3还需要迁移invoke_execute
        # 暂时简化：直接调用execute（后续迁移invoke.py）
        return pool.submit(self._execute, context)

    def shutdown(self, *, wait: bool = True, timeout: float | None = None) -> None:
        del timeout
        if self._pool is None:
            return
        try:
            self._pool.shutdown(wait=wait, cancel_futures=not wait)
        except Exception:
            pass
        self._pool = None

    def get_stats(self) -> dict[str, Any]:
        return {
            "backend": ExecutionBackend.PROCESS.value,
            "max_workers": self._max_workers,
            "submitted": self._submitted,
        }


class ThreadJobExecutor:
    """ThreadPoolExecutor实现。"""

    def __init__(
        self,
        *,
        max_workers: int,
        execute: ExecuteFn,
    ) -> None:
        self._max_workers = max(1, int(max_workers))
        self._execute = execute
        self._pool: ThreadPoolExecutor | None = None
        self._submitted = 0

    @property
    def max_workers(self) -> int:
        return self._max_workers

    @property
    def requires_picklable_payload(self) -> bool:
        return False

    def _ensure_pool(self) -> ThreadPoolExecutor:
        if self._pool is None:
            self._pool = ThreadPoolExecutor(max_workers=self._max_workers)
        return self._pool

    def submit(self, context: JobContext) -> Future:
        self._submitted += 1
        pool = self._ensure_pool()
        return pool.submit(self._execute, context)

    def shutdown(self, *, wait: bool = True, timeout: float | None = None) -> None:
        del timeout
        if self._pool is None:
            return
        try:
            self._pool.shutdown(wait=wait)
        except Exception:
            pass
        self._pool = None

    def get_stats(self) -> dict[str, Any]:
        return {
            "backend": ExecutionBackend.THREAD.value,
            "max_workers": self._max_workers,
            "submitted": self._submitted,
        }


__all__ = [
    "JobExecutor",
    "create_job_executor",
    "ProcessJobExecutor",
    "ThreadJobExecutor",
]