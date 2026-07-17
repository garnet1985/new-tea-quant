"""Picklable worker execute adapters for timeline vs opaque execute_fn."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Protocol

from core.modules.backtest_engine.core.shared.types import JobContext
from core.modules.backtest_engine.core.timeline.driver import TimelineDriver
from core.modules.backtest_engine.core.timeline.hooks import TimelineHooks

ExecuteFnLike = Callable[[JobContext], Any]


class TimelineHooksFactory(Protocol):
    """可 pickle 的 factory：JobContext → TimelineHooks。"""

    def __call__(self, job_context: JobContext) -> TimelineHooks:
        ...


class TimelineWorkerExecute:
    """可 pickle 的 ExecuteFn：包装 TimelineHooksFactory → TimelineDriver。"""

    def __init__(self, factory: TimelineHooksFactory) -> None:
        self.factory = factory

    def __call__(self, job_context: JobContext) -> Dict[str, Any]:
        hooks = self.factory(job_context)
        return TimelineDriver.run_for_job(job_context, hooks)


class WorkerExecuteResolver:
    """Facade 用：execute_fn 与 timeline_hooks_factory 二选一。"""

    @staticmethod
    def resolve(
        *,
        execute_fn: Optional[ExecuteFnLike] = None,
        timeline_hooks_factory: Optional[TimelineHooksFactory] = None,
    ) -> ExecuteFnLike:
        has_exec = execute_fn is not None
        has_timeline = timeline_hooks_factory is not None
        if has_exec == has_timeline:
            raise ValueError(
                "BacktestEngine.run 需要恰好其一: execute_fn 或 timeline_hooks_factory"
            )
        if timeline_hooks_factory is not None:
            return TimelineWorkerExecute(timeline_hooks_factory)
        assert execute_fn is not None
        return execute_fn


__all__ = [
    "TimelineHooksFactory",
    "TimelineWorkerExecute",
    "WorkerExecuteResolver",
]
