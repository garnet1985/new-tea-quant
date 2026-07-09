"""
Backtest Engine - entity_based Executor (DuckDB Branch)

DuckDB ProcessPool scope 包装；执行逻辑委托 ``EntityExecutor``。
"""
from __future__ import annotations

from typing import Any, Callable, List, Optional

from core.modules.backtest_engine.core.shared.context import ExecutionContext
from core.modules.backtest_engine.core.shared.duckdb_executor_scope import (
    execute_with_duckdb_process_pool_scope,
)
from core.modules.backtest_engine.core.entity_based.executor import EntityExecutor
from core.modules.backtest_engine.core.entity_based.planner import DispatchPlan, JobBatch
from core.modules.backtest_engine.core.shared.types import ExecuteFn, ChildProcessTaskStartFn, ChildProcessTaskCompleteFn


class EntityExecutorDuckDB(EntityExecutor):
    """entity_based 执行器 + DuckDB ProcessPool scope。"""

    @staticmethod
    def execute(
        plan: DispatchPlan,
        batches: List[JobBatch],
        context: ExecutionContext,
        execute_fn: EntityExecutor.ExecuteFn,
        on_single_task_result: Optional[EntityExecutor.OnSingleTaskResultHook] = None,
        on_after_all_tasks_complete: Optional[EntityExecutor.OnAfterAllTasksCompleteHook] = None,
        on_child_process_task_start: Optional[ChildProcessTaskStartFn] = None,
        on_child_process_task_complete: Optional[ChildProcessTaskCompleteFn] = None,
        log_label: str = "执行",
        *,
        data_mgr: Optional[Any] = None,
        duckdb_process_pool_scope: str = "auto",
        duckdb_resume_main_after_pool: bool = True,
        admission_limit: Optional[int] = None,
        get_admission_limit: Optional[Callable[[], int]] = None,
    ) -> EntityExecutor.ExecutionResult:
        return execute_with_duckdb_process_pool_scope(
            EntityExecutor.execute,
            data_mgr=data_mgr,
            duckdb_process_pool_scope=duckdb_process_pool_scope,
            duckdb_resume_main_after_pool=duckdb_resume_main_after_pool,
            plan=plan,
            batches=batches,
            context=context,
            execute_fn=execute_fn,
            on_single_task_result=on_single_task_result,
            on_after_all_tasks_complete=on_after_all_tasks_complete,
            on_child_process_task_start=on_child_process_task_start,
            on_child_process_task_complete=on_child_process_task_complete,
            log_label=log_label,
            admission_limit=admission_limit,
            get_admission_limit=get_admission_limit,
        )


__all__ = ["EntityExecutorDuckDB"]
