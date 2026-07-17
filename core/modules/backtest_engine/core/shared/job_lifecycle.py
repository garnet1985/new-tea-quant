"""BacktestEngine task 生命周期：before_start → execute → after_complete。"""
from __future__ import annotations

from typing import Any, Optional

from core.modules.backtest_engine.core.shared.types import (
    ExecuteFn,
    JobContext,
    TaskCompleteFn,
    TaskStartFn,
)


def run_job_lifecycle(
    execute_fn: ExecuteFn,
    job_context: JobContext,
    *,
    on_before_task_start: Optional[TaskStartFn] = None,
    on_after_task_complete: Optional[TaskCompleteFn] = None,
) -> Any:
    """在工作单元内：可选 init → execute_fn → 可选 release。"""
    if on_before_task_start is not None:
        job_context.init = on_before_task_start(job_context)
    try:
        return execute_fn(job_context)
    finally:
        if on_after_task_complete is not None:
            on_after_task_complete(job_context)


__all__ = ["TaskStartFn", "TaskCompleteFn", "run_job_lifecycle"]
