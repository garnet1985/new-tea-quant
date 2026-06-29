"""SliceExecutorDuckDB scope wrapper tests."""
from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import patch

from core.modules.backtest_engine.core.shared.context import ExecutionContext
from core.modules.backtest_engine.core.slice_based.executor import SliceExecutor
from core.modules.backtest_engine.core.slice_based.executor_duckdb import (
    SliceExecutorDuckDB,
)
from core.modules.backtest_engine.core.slice_based.planner import (
    SliceDispatchPlan,
    SliceJobBatch,
)


def _plan() -> SliceDispatchPlan:
    return SliceDispatchPlan(
        reader_workers=2,
        reader_memory_budget_mb=40.0,
        compute_processes=1,
        compute_memory_budget_mb=30.0,
        queue_capacity=4,
        preload_depth=2,
        slice_open_days=20,
        dispatch_jobs=2,
        memory_budget_mb=4096.0,
        oom_adjusted=False,
    )


def test_duckdb_executor_wraps_scope_and_delegates() -> None:
    plan = _plan()
    context = ExecutionContext.create(run_name="test", total_jobs=0)
    expected = SliceExecutor.ExecutionResult(
        success=True,
        total_jobs=0,
        completed_jobs=0,
        failed_jobs=0,
        failures=[],
        elapsed_seconds=0.0,
        job_results=[],
    )
    scope_calls: list[dict] = []

    @contextmanager
    def fake_scope(**kwargs):
        scope_calls.append(kwargs)
        yield

    with patch(
        "core.infra.db.engines.duckdb.process_pool_scope.should_apply_process_pool_scope",
        return_value=True,
    ), patch(
        "core.infra.db.engines.duckdb.process_pool_scope.maybe_duckdb_worker_pool_scope",
        side_effect=fake_scope,
    ), patch.object(
        SliceExecutor,
        "execute",
        return_value=expected,
    ) as execute_mock:
        result = SliceExecutorDuckDB.execute(
            plan,
            [],
            context,
            execute_fn=lambda ctx: {"success": True},
            data_mgr=object(),
            duckdb_process_pool_scope="auto",
            duckdb_resume_main_after_pool=False,
        )

    assert result is expected
    execute_mock.assert_called_once()
    assert len(scope_calls) == 1
    assert scope_calls[0]["use_process_pool"] is True
    assert scope_calls[0]["resume_main_after"] is False
