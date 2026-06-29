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


def test_sliced_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="sliced mode"):
        BacktestEngine.sliced.run(
            [],
            _noop_execute,
            executor_key="tag",
        )


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
