"""entity_based job executor（task 生命周期钩子；日推进由 BE TimelineDriver）。"""
from __future__ import annotations

from typing import Any, List

from core.modules.strategy.core.engines.enumerator.shared.base_executor import (
    BaseJobExecutor,
    ExecutorHooksContext,
)


class JobExecutor(BaseJobExecutor):
    """entity_based task 钩子集合。

    边界:
    - 负责: mode 专有调度日志；probe 跳过 flush
    - 不负责: 日历日循环（TimelineDriver）、Investment（EntityTimelineHooks）
    - 调用方: EnumeratorPipeline → BacktestEngine.entity_based
    """

    task_log_label = "子进程task"

    @classmethod
    def on_before_all_tasks_start(cls, plan: Any, batches: List[Any]) -> None:
        print(
            f"  调度: {len(batches)} batches, "
            f"~{getattr(plan, 'entities_per_job', '?')} entities/job, "
            f"workers={getattr(plan, 'max_workers', '?')}",
            flush=True,
        )

    @classmethod
    def on_after_task_complete(cls, job_context: Any) -> None:
        if job_context.payload.get("_dispatch_probe"):
            return
        cls.flush_job_investments(job_context)


__all__ = ["ExecutorHooksContext", "JobExecutor"]
