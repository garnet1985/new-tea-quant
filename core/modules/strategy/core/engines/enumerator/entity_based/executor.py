"""entity_based job executor（task 生命周期钩子；日推进由 BE + AdvancementHooks）。"""
from __future__ import annotations

from typing import Any, Dict, List

from core.modules.strategy.core.engines.enumerator.shared.executor_hooks import (
    ExecutorHooks,
    ExecutorHooksContext,
)


class JobExecutor:
    """entity_based task 钩子集合。

    边界:
    - 负责: RunCallbacks（load / flush / 进度）；advancement factory 入口
    - 不负责: 日历日循环（CalendarAdvancer）、Investment 细节（EntityAdvancementHooks）
    - 调用方: EnumeratorPipeline → BacktestEngine.entity_based
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
    def advancement_hooks_factory(job_context: Any) -> Any:
        from core.modules.strategy.core.engines.enumerator.entity_based.advancement import (
            build_entity_advancement_hooks,
        )

        return build_entity_advancement_hooks(job_context)

    @staticmethod
    def on_before_all_tasks_start(plan: Any, batches: List[Any]) -> None:
        print(
            f"  调度: {len(batches)} batches, "
            f"~{getattr(plan, 'entities_per_job', '?')} entities/job, "
            f"workers={getattr(plan, 'max_workers', '?')}",
            flush=True,
        )

    @staticmethod
    def on_before_task_start(job_context: Any) -> Dict[str, Any]:
        return ExecutorHooks.load_bundle_data(job_context, log_label="子进程task")

    @staticmethod
    def on_after_task_complete(job_context: Any) -> None:
        if job_context.payload.get("_dispatch_probe"):
            return
        ExecutorHooks.flush_job_investments(job_context)


__all__ = ["ExecutorHooksContext", "JobExecutor"]
