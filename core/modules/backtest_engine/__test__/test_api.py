"""BacktestEngine facade API smoke tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import JobContext, JobReport, RunCallbacks, RunProgress
from core.modules.backtest_engine.core.timeline_based.execute_pipeline import (
    TimelineExecutePipeline,
)
from core.modules.backtest_engine.core.timeline_based.executor import TimelineExecutor


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
    assert hasattr(BacktestEngine, "entity_based")
    assert hasattr(BacktestEngine, "slice_based")
    assert BacktestEngine.Mode.ENTITY_BASED.value == "entity_based"
    assert BacktestEngine.Mode.SLICE_BASED.value == "slice_based"


def test_mode_normalize() -> None:
    assert BacktestEngine.Mode.normalize(BacktestEngine.Mode.ENTITY_BASED) == "entity_based"
    assert BacktestEngine.Mode.normalize("slice_based") == "slice_based"


def test_mode_normalize_rejects_legacy_alias() -> None:
    with pytest.raises(ValueError, match="unknown backtest mode"):
        BacktestEngine.Mode.normalize("timeline")


def test_run_accepts_mode_enum() -> None:
    result = BacktestEngine.run(
        BacktestEngine.Mode.ENTITY_BASED,
        [],
        _noop_execute,
    )
    assert result.mode == "entity_based"


def test_run_unknown_mode_raises() -> None:
    with pytest.raises(ValueError, match="unknown backtest mode"):
        BacktestEngine.run(
            "invalid",
            [],
            _noop_execute,
        )


def test_entity_based_empty_jobs_returns_success() -> None:
    result = BacktestEngine.entity_based.run([], _noop_execute)
    assert isinstance(result, BacktestEngine.RunResult)
    assert result.mode == "entity_based"
    assert result.success is True
    assert result.total_jobs == 0


def test_slice_based_bulk_job_embeds_slice_plan() -> None:
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
    result = BacktestEngine.slice_based.run(jobs, _sliced_execute)
    assert result.success is True
    assert result.total_jobs == 1
    assert result.completed_jobs == 1
    assert result.plan is not None
    assert result.plan.slice_open_days == 20
    assert result.plan.dispatch_jobs == 2
    assert result.job_results[0].data["reader_workers"] is not None


def test_slice_based_empty_jobs_returns_success() -> None:
    result = BacktestEngine.slice_based.run([], _sliced_execute)
    assert isinstance(result, BacktestEngine.RunResult)
    assert result.mode == "slice_based"
    assert result.success is True
    assert result.total_jobs == 0


def test_run_callbacks_forward_on_result() -> None:
    seen: list[str] = []

    def on_result(report, progress) -> None:
        seen.append(report.job_id)

    mock_execution = TimelineExecutor.ExecutionResult(
        success=True,
        total_jobs=1,
        completed_jobs=1,
        failed_jobs=0,
        failures=[],
        elapsed_seconds=0.0,
        job_results=[],
    )
    mock_result = TimelineExecutePipeline.Result(
        plan=MagicMock(),
        batches=[],
        monitor_config=MagicMock(),
        execution=mock_execution,
    )

    jobs = [
        {
            "id": "000001.SZ",
            "payload": {"stock_id": "000001.SZ"},
        }
    ]

    def fake_run(_self, _jobs, _performance, **kwargs):
        hook = kwargs.get("on_result")
        if hook is not None:
            hook(
                JobReport(job_id="000001.SZ", success=True),
                RunProgress(finished=1, total=1, ok=1, fail=0),
            )
        return mock_result

    with patch.object(TimelineExecutePipeline, "run", fake_run):
        BacktestEngine.entity_based.run(
            jobs,
            _noop_execute,
            task_name="demo",
            callbacks=RunCallbacks(on_result=on_result),
        )

    assert seen == ["000001.SZ"]
