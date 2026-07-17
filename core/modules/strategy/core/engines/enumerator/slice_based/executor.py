"""slice_based job executor（task 生命周期钩子；日推进由 BE TimelineDriver）。"""
from __future__ import annotations

from typing import Any, Dict, List

from core.modules.strategy.core.engines.enumerator.shared.executor_hooks import (
    ExecutorHooks,
    ExecutorHooksContext,
)


class JobExecutor:
    """slice_based task 钩子集合。

    边界:
    - 负责: RunCallbacks（load / flush / 进度）
    - 不负责: 日历日循环（TimelineDriver）、asof/Investment（SliceTimelineHooks）
    - 调用方: EnumeratorPipeline → BacktestEngine.slice_based
    """

    @staticmethod
    def build_run_callbacks(ctx: ExecutorHooksContext) -> Any:
        return ExecutorHooks.build_run_callbacks(
            ctx,
            on_before_all_tasks_start=JobExecutor.on_before_all_tasks_start,
            on_before_task_start=JobExecutor.on_before_task_start,
            on_after_task_complete=JobExecutor.on_after_task_complete,
            on_after_all_tasks_complete=ExecutorHooks.on_after_all_tasks_complete,
            on_task_result=ExecutorHooks.on_task_result,
        )

    @staticmethod
    def on_before_all_tasks_start(plan: Any, batches: List[Any]) -> None:
        print(
            f"  调度: {len(batches)} batches, "
            f"slice_open_days={getattr(plan, 'slice_open_days', '?')}, "
            f"reader_workers={getattr(plan, 'reader_workers', '?')}",
            flush=True,
        )

    @staticmethod
    def on_before_task_start(job_context: Any) -> Dict[str, Any]:
        return ExecutorHooks.load_bundle_data(job_context, log_label="slice task")

    @staticmethod
    def on_after_task_complete(job_context: Any) -> None:
        ExecutorHooks.flush_job_investments(job_context)


__all__ = ["ExecutorHooksContext", "JobExecutor"]
