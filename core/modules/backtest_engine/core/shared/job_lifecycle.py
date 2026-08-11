"""BacktestEngine task 生命周期：start → execute → complete。"""
from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.backtest_engine.core.shared.types import (
    ExecuteFn,
    JobContext,
    TaskCompleteFn,
    TaskStartFn,
)


class JobLifecycle:
    """Task 侧生命周期（挂靠类；不导出自由函数）。

    ``on_task_start`` → ``execute_fn`` → ``on_task_complete``。
    ``on_task_complete`` 若返回 dict，成功路径下并入结果。
    """

    @staticmethod
    def run(
        execute_fn: ExecuteFn,
        job_context: JobContext,
        *,
        on_task_start: Optional[TaskStartFn] = None,
        on_task_complete: Optional[TaskCompleteFn] = None,
    ) -> Any:
        if on_task_start is not None:
            job_context.init = on_task_start(job_context)
        try:
            raw = execute_fn(job_context)
        except Exception:
            if on_task_complete is not None:
                on_task_complete(job_context)
            raise
        return JobLifecycle._merge_complete(raw, job_context, on_task_complete)

    @staticmethod
    def merge_complete_extra(raw: Any, extra: Any) -> Any:
        if not isinstance(extra, dict):
            return raw
        if isinstance(raw, dict):
            return {**raw, **extra}
        return dict(extra)

    @staticmethod
    def _merge_complete(
        raw: Any,
        job_context: JobContext,
        on_task_complete: Optional[TaskCompleteFn],
    ) -> Any:
        if on_task_complete is None:
            return raw
        extra = on_task_complete(job_context)
        return JobLifecycle.merge_complete_extra(raw, extra)


__all__ = ["JobLifecycle"]
