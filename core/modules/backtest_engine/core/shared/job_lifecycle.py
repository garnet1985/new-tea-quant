"""BacktestEngine 子进程 job 生命周期：init → execute → release。"""
from __future__ import annotations

from typing import Any, Callable, Optional

from core.modules.backtest_engine.core.shared.types import ExecuteFn, JobContext

JobInitFn = Callable[[JobContext], Any]
JobReleaseFn = Callable[[JobContext], None]


def run_job_lifecycle(
    execute_fn: ExecuteFn,
    job_context: JobContext,
    *,
    on_job_init: Optional[JobInitFn] = None,
    on_job_release: Optional[JobReleaseFn] = None,
) -> Any:
    """在子进程内：可选 init → execute_fn → 可选 release。"""
    if on_job_init is not None:
        job_context.init = on_job_init(job_context)
    try:
        return execute_fn(job_context)
    finally:
        if on_job_release is not None:
            on_job_release(job_context)


__all__ = ["JobInitFn", "JobReleaseFn", "run_job_lifecycle"]
