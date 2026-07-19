"""BacktestEngine facade API smoke tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import JobContext, JobReport, RunCallbacks, RunProgress
from core.modules.backtest_engine.core.schedule.entity_based.execute_pipeline import (
    EntityExecutePipeline,
)
from core.modules.backtest_engine.core.schedule.entity_based.executor import EntityExecutor


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
                "timeline_point_count": 40,
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


def test_run_callbacks_forward_on_before_task_start_and_complete() -> None:
    phases: list[str] = []

    def on_before_task_start(context: JobContext) -> str:
        phases.append("init")
        return "session"

    def on_after_task_complete(context: JobContext) -> None:
        phases.append("release")
        assert context.init == "session"

    def execute(context: JobContext) -> dict:
        phases.append("execute")
        assert context.init == "session"
        return {"success": True}

    from core.modules.backtest_engine.core.shared.job_lifecycle import run_job_lifecycle

    ctx = JobContext(job_id="j1", payload={"entity_id": "000001.SZ"})
    run_job_lifecycle(
        execute,
        ctx,
        on_before_task_start=on_before_task_start,
        on_after_task_complete=on_after_task_complete,
    )
    assert phases == ["init", "execute", "release"]


def test_run_callbacks_forward_on_task_result() -> None:
    seen: list[str] = []

    def on_task_result(report, progress) -> None:
        seen.append(report.job_id)

    mock_execution = EntityExecutor.ExecutionResult(
        success=True,
        total_jobs=1,
        completed_jobs=1,
        failed_jobs=0,
        failures=[],
        elapsed_seconds=0.0,
        job_results=[],
    )
    mock_result = EntityExecutePipeline.Result(
        plan=MagicMock(),
        batches=[],
        monitor_config=MagicMock(),
        execution=mock_execution,
    )

    jobs = [
        {
            "id": "job-1",
            "payload": {
                "entity_specified": [{"id": "000001.SZ"}],
            },
        }
    ]

    def fake_run(_self, _jobs, _performance, **kwargs):
        hook = kwargs.get("on_task_result")
        if hook is not None:
            hook(
                JobReport(job_id="job-1", success=True),
                RunProgress(finished=1, total=1, ok=1, fail=0),
            )
        return mock_result

    with patch.object(EntityExecutePipeline, "run", fake_run):
        BacktestEngine.entity_based.run(
            jobs,
            _noop_execute,
            task_name="demo",
            callbacks=RunCallbacks(on_task_result=on_task_result),
        )

    assert seen == ["job-1"]


def test_worker_execute_resolver_xor() -> None:
    from core.modules.backtest_engine.core.timeline.worker import WorkerExecuteResolver

    with pytest.raises(ValueError, match="恰好其一"):
        WorkerExecuteResolver.resolve()
    with pytest.raises(ValueError, match="恰好其一"):
        WorkerExecuteResolver.resolve(
            execute_fn=_noop_execute,
            timeline_hooks_factory=lambda ctx: None,
        )
    WorkerExecuteResolver.resolve(execute_fn=_noop_execute)
    WorkerExecuteResolver.resolve(timeline_hooks_factory=lambda ctx: None)


def test_timeline_driver_tick_order() -> None:
    from core.modules.backtest_engine.core.timeline.driver import TimelineDriver
    from core.modules.backtest_engine.core.timeline.timeline import Timeline

    events: list[str] = []

    class Hooks:
        def resolve_timeline(self, job_context):
            raise AssertionError("run() 不走 resolve_timeline")

        def on_run_begin(self, timeline):
            events.append(f"begin:{len(timeline.points)}")

        def on_tick(self, point, index, *, is_last):
            events.append(f"tick:{point}:{index}:{is_last}")

        def on_run_end(self, timeline):
            events.append(f"end:{len(timeline.points)}")
            return {"success": True, "n": len(timeline.points)}

    result = TimelineDriver.run(
        timeline=Timeline.from_points(
            ["20240101", "20240102", "20240103", "20240110"],
            start="20240102",
            end="20240103",
        ),
        hooks=Hooks(),
    )
    assert result == {"success": True, "n": 2}
    assert events == [
        "begin:2",
        "tick:20240102:0:False",
        "tick:20240103:1:True",
        "end:2",
    ]


def test_entity_based_rejects_missing_worker() -> None:
    with pytest.raises(ValueError, match="恰好其一"):
        BacktestEngine.entity_based.run([], performance={"max_workers": 1})
