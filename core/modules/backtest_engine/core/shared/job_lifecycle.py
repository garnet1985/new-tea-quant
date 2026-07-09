"""BacktestEngine 子进程 job 生命周期：init → execute → release。"""
from __future__ import annotations

from typing import Any, Callable, Optional

from core.modules.backtest_engine.core.shared.types import ExecuteFn, JobContext, ChildProcessTaskStartFn, ChildProcessTaskCompleteFn


def run_job_lifecycle(
    execute_fn: ExecuteFn,
    job_context: JobContext,
    *,
    on_child_process_task_start: Optional[ChildProcessTaskStartFn] = None,
    on_child_process_task_complete: Optional[ChildProcessTaskCompleteFn] = None,
) -> Any:
    """在子进程内：可选 init → execute_fn → 可选 release。"""
    if on_child_process_task_start is not None:
        job_context.init = on_child_process_task_start(job_context)
    try:
        return execute_fn(job_context)
    finally:
        if on_child_process_task_complete is not None:
            on_child_process_task_complete(job_context)


__all__ = ["ChildProcessTaskStartFn", "ChildProcessTaskCompleteFn", "run_job_lifecycle"]
