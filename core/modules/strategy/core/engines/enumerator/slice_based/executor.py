"""slice_based job executor（task 生命周期钩子；日推进由 BE Timeline.drive）。"""
from __future__ import annotations

from typing import Any, List

from core.modules.strategy.core.engines.enumerator.shared.base_executor import (
    BaseJobExecutor,
    ExecutorHooksContext,
)
from core.modules.strategy.core.engines.enumerator.slice_based.timeline import (
    SliceTimelineHooks,
)


class JobExecutor(BaseJobExecutor):
    """slice_based task 钩子集合。

    边界:
    - 负责: mode 专有调度日志；on_tick → SliceTimelineHooks
    - 不负责: 日历日循环（Timeline.drive）
    - 调用方: EnumeratorPipeline → BacktestEngine.slice_based
    """

    task_log_label = "slice task"
    timeline_hooks_cls = SliceTimelineHooks

    @classmethod
    def on_before_all_tasks_start(cls, plan: Any, batches: List[Any]) -> None:
        print(
            f"  调度: {len(batches)} batches, "
            f"slice_open_days={getattr(plan, 'slice_open_days', '?')}, "
            f"reader_workers={getattr(plan, 'reader_workers', '?')}",
            flush=True,
        )


__all__ = ["ExecutorHooksContext", "JobExecutor"]
