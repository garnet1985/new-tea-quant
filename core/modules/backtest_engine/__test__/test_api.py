"""BacktestEngine facade API smoke tests."""
from __future__ import annotations

import pytest

from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.core.shared.types import JobContext


def _noop_execute(context: JobContext) -> dict:
    jobs = context.payload.get("jobs") or []
    return {
        "success": True,
        "job_id": context.job_id,
        "entities_count": len(jobs),
    }


def _sliced_execute(context: JobContext) -> dict:
    slice_plan = context.payload.get("_slice_plan") or {}
    return {
        "success": True,
        "job_id": context.job_id,
        "slices_count": slice_plan.get("dispatch_jobs", 1),
        "reader_workers": slice_plan.get("reader_workers"),
    }


def test_facade_export() -> None:
    assert BacktestEngine is not None
    assert hasattr(BacktestEngine, "timeline")
    assert hasattr(BacktestEngine, "sliced")


def test_run_unknown_mode_raises() -> None:
    with pytest.raises(ValueError, match="unknown backtest mode"):
        BacktestEngine.run(
            mode="invalid",
            jobs=[],
            execute_fn=_noop_execute,
            executor_key="tag",
        )


def test_sliced_empty_jobs_returns_success() -> None:
    result = BacktestEngine.sliced.run(
        [],
        _sliced_execute,
        executor_key="tag",
    )
    assert isinstance(result, BacktestEngine.RunResult)
    assert result.mode == "sliced"
    assert result.success is True
    assert result.total_jobs == 0


def test_sliced_bulk_job_embeds_slice_plan() -> None:
    jobs = [
        {
            "id": "tag_calendar_slice",
            "payload": {
                "tag_execution_mode": "calendar_slice",
                "entity_ids": ["000001.SZ"],
                "open_dates": [f"202401{d:02d}" for d in range(1, 41)],
            },
        }
    ]
    result = BacktestEngine.sliced.run(
        jobs,
        _sliced_execute,
        executor_key="tag",
    )
    assert result.success is True
    assert result.total_jobs == 1
    assert result.completed_jobs == 1
    assert result.plan is not None
    assert result.plan.slice_open_days == 20
    assert result.plan.dispatch_jobs == 2
    assert result.job_results[0].data["reader_workers"] is not None


def test_timeline_empty_jobs_returns_success() -> None:
    result = BacktestEngine.timeline.run(
        [],
        _noop_execute,
        executor_key="tag",
    )
    assert isinstance(result, BacktestEngine.RunResult)
    assert result.mode == "timeline"
    assert result.success is True
    assert result.total_jobs == 0


def test_unknown_executor_key_raises() -> None:
    with pytest.raises(ValueError, match="unknown executor_key"):
        BacktestEngine.timeline.run(
            [],
            _noop_execute,
            executor_key="unknown.worker",
        )
    with pytest.raises(ValueError, match="unknown executor_key"):
        BacktestEngine.sliced.run(
            [],
            _sliced_execute,
            executor_key="unknown.worker",
        )
