"""
Backtest Engine - Timeline-based Executor (DuckDB Branch)

DuckDB ProcessPool scope 包装；执行逻辑委托 ``TimelineExecutor``。
"""
from __future__ import annotations

import logging
from typing import Any, Callable, List, Optional

from core.modules.backtest_engine.core.shared.context import ExecutionContext
from core.modules.backtest_engine.core.timeline_based.executor import TimelineExecutor
from core.modules.backtest_engine.core.timeline_based.planner import DispatchPlan, JobBatch

logger = logging.getLogger(__name__)


class TimelineExecutorDuckDB(TimelineExecutor):
    """Timeline 执行器 + DuckDB ProcessPool scope。"""

    @staticmethod
    def execute(
        plan: DispatchPlan,
        batches: List[JobBatch],
        context: ExecutionContext,
        execute_fn: TimelineExecutor.ExecuteFn,
        on_result: Optional[TimelineExecutor.OnResultHook] = None,
        on_release: Optional[TimelineExecutor.OnReleaseHook] = None,
        log_label: str = "执行",
        *,
        data_mgr: Optional[Any] = None,
        duckdb_process_pool_scope: str = "auto",
        duckdb_resume_main_after_pool: bool = True,
        admission_limit: Optional[int] = None,
        get_admission_limit: Optional[Callable[[], int]] = None,
    ) -> TimelineExecutor.ExecutionResult:
        from core.infra.db.engines.duckdb.process_pool_scope import (
            maybe_duckdb_worker_pool_scope,
            should_apply_process_pool_scope,
        )

        use_scope = should_apply_process_pool_scope(
            mode=duckdb_process_pool_scope,  # type: ignore[arg-type]
            use_process_pool=True,
            data_mgr=data_mgr,
        )
        if use_scope:
            logger.info(
                "%s DuckDB ProcessPool scope enabled (mode=%s)",
                log_label,
                duckdb_process_pool_scope,
            )
        else:
            logger.debug(
                "%s DuckDB ProcessPool scope skipped (mode=%s)",
                log_label,
                duckdb_process_pool_scope,
            )

        execute_kwargs = {
            "execute_fn": execute_fn,
            "on_result": on_result,
            "on_release": on_release,
            "log_label": log_label,
            "admission_limit": admission_limit,
            "get_admission_limit": get_admission_limit,
        }

        with maybe_duckdb_worker_pool_scope(
            mode=duckdb_process_pool_scope,  # type: ignore[arg-type]
            use_process_pool=True,
            data_mgr=data_mgr,
            resume_main_after=duckdb_resume_main_after_pool,
        ):
            return TimelineExecutor.execute(plan, batches, context, **execute_kwargs)


__all__ = ["TimelineExecutorDuckDB"]
