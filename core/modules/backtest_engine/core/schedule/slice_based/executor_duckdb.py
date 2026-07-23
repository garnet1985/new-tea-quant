"""
Backtest Engine - Slice-based Executor (DuckDB Branch)

DuckDB ProcessPool scope wrapper; execution delegates to ``SliceExecutor``.
"""
from __future__ import annotations

from typing import Any, List, Optional

from core.modules.backtest_engine.core.shared.context import ExecutionContext
from core.modules.backtest_engine.core.shared.duckdb_executor_scope import (
    execute_with_duckdb_process_pool_scope,
)
from core.modules.backtest_engine.core.shared.types import TaskCompleteFn, TaskStartFn
from core.modules.backtest_engine.core.schedule.slice_based.executor import SliceExecutor
from core.modules.backtest_engine.core.schedule.slice_based.planner import (
    SliceDispatchPlan,
    SliceJobBatch,
)


class SliceExecutorDuckDB(SliceExecutor):
    """Slice executor + DuckDB ProcessPool scope."""

    @staticmethod
    def execute(
        plan: SliceDispatchPlan,
        batches: List[SliceJobBatch],
        context: ExecutionContext,
        execute_fn: SliceExecutor.ExecuteFn,
        on_result: Optional[SliceExecutor.OnResultHook] = None,
        on_before_task_start: Optional[TaskStartFn] = None,
        on_after_task_complete: Optional[TaskCompleteFn] = None,
        log_label: str = "切片执行",
        *,
        data_mgr: Optional[Any] = None,
        progress_reporter: Optional[Any] = None,
        duckdb_process_pool_scope: str = "auto",
        duckdb_resume_main_after_pool: bool = True,
    ) -> SliceExecutor.ExecutionResult:
        return execute_with_duckdb_process_pool_scope(
            SliceExecutor.execute,
            data_mgr=data_mgr,
            duckdb_process_pool_scope=duckdb_process_pool_scope,
            duckdb_resume_main_after_pool=duckdb_resume_main_after_pool,
            plan=plan,
            batches=batches,
            context=context,
            execute_fn=execute_fn,
            on_result=on_result,
            on_before_task_start=on_before_task_start,
            on_after_task_complete=on_after_task_complete,
            log_label=log_label,
            progress_reporter=progress_reporter,
        )


__all__ = ["SliceExecutorDuckDB"]
