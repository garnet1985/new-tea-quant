"""
Backtest Engine - Slice-based Executor (DuckDB Branch)

DuckDB ProcessPool scope wrapper; execution delegates to ``SliceExecutor``.
"""
from __future__ import annotations

import logging
from typing import Any, List, Optional

from core.modules.backtest_engine.core.shared.context import ExecutionContext
from core.modules.backtest_engine.core.slice_based.executor import SliceExecutor
from core.modules.backtest_engine.core.slice_based.planner import (
    SliceDispatchPlan,
    SliceJobBatch,
)

logger = logging.getLogger(__name__)


class SliceExecutorDuckDB(SliceExecutor):
    """Slice executor + DuckDB ProcessPool scope."""

    @staticmethod
    def execute(
        plan: SliceDispatchPlan,
        batches: List[SliceJobBatch],
        context: ExecutionContext,
        execute_fn: SliceExecutor.ExecuteFn,
        on_result: Optional[SliceExecutor.OnResultHook] = None,
        log_label: str = "切片执行",
        *,
        data_mgr: Optional[Any] = None,
        duckdb_process_pool_scope: str = "auto",
        duckdb_resume_main_after_pool: bool = True,
    ) -> SliceExecutor.ExecutionResult:
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
            "log_label": log_label,
        }

        with maybe_duckdb_worker_pool_scope(
            mode=duckdb_process_pool_scope,  # type: ignore[arg-type]
            use_process_pool=True,
            data_mgr=data_mgr,
            resume_main_after=duckdb_resume_main_after_pool,
        ):
            return SliceExecutor.execute(plan, batches, context, **execute_kwargs)


__all__ = ["SliceExecutorDuckDB"]
