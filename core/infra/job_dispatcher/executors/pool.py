"""Process / Thread 池 JobExecutor 实现。"""
from __future__ import annotations

import multiprocessing as mp
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from typing import Any, Callable, Optional

from core.infra.job_dispatcher.hooks import ExecuteFn
from core.infra.job_dispatcher.types import ExecutionBackend, JobContext
from core.infra.job_dispatcher.worker_invoke import invoke_execute


class ProcessJobExecutor:
    """多进程 JobExecutor。"""

    def __init__(
        self,
        *,
        max_workers: int,
        execute: ExecuteFn,
        start_method: str = "spawn",
        timeout: Optional[float] = None,
    ) -> None:
        self._max_workers = max(1, int(max_workers))
        self._execute = execute
        self._start_method = start_method
        self._timeout = timeout
        self._pool: Optional[ProcessPoolExecutor] = None
        self._submitted = 0
        self._completed = 0
        self._failed = 0

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
        return pool.submit(invoke_execute, self._execute, context)

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
            "completed": self._completed,
            "failed": self._failed,
        }


class ThreadJobExecutor:
    """多线程 JobExecutor。"""

    def __init__(
        self,
        *,
        max_workers: int,
        execute: ExecuteFn,
    ) -> None:
        self._max_workers = max(1, int(max_workers))
        self._execute = execute
        self._pool: Optional[ThreadPoolExecutor] = None
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
        return pool.submit(invoke_execute, self._execute, context)

    def shutdown(self, *, wait: bool = True, timeout: float | None = None) -> None:
        del timeout
        if self._pool is not None:
            self._pool.shutdown(wait=wait, cancel_futures=not wait)
            self._pool = None

    def get_stats(self) -> dict[str, Any]:
        return {
            "backend": ExecutionBackend.THREAD.value,
            "max_workers": self._max_workers,
            "submitted": self._submitted,
        }
