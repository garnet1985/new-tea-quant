"""BacktestEngine facade API smoke tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.modules.backtest_engine import BacktestEngine
from core.modules.backtest_engine.contracts import (
    JobContext,
    JobReport,
    RunCallbacks,
    RunProgress,
    Timeline,
    EntityMonitorStats,
    ENGINE_PERF_KEY,
    ENUM_PERF_KEY,
    WorkerTaskPerf,
)
from core.modules.backtest_engine.core.schedule.entity_based.execute_pipeline import (
    EntityExecutePipeline,
)
from core.modules.backtest_engine.core.schedule.entity_based.executor import EntityExecutor

pytestmark = pytest.mark.force_run


def _noop_on_tick(context: JobContext, point: str, index: int) -> None:
    _ = (context, point, index)


def test_facade_export() -> None:
    assert BacktestEngine is not None
    assert hasattr(BacktestEngine, "entity_based")
    assert hasattr(BacktestEngine, "slice_based")
    assert hasattr(BacktestEngine, "Performance")
    assert BacktestEngine.Mode.ENTITY_BASED.value == "entity_based"
    assert BacktestEngine.Mode.SLICE_BASED.value == "slice_based"
    assert BacktestEngine.Performance.Profiles.TAG == "tag"
    assert callable(BacktestEngine.Performance.resolve_entity_based_for_profile)
    assert callable(BacktestEngine.Performance.calendar_slice_config)
    assert ENGINE_PERF_KEY == "engine_perf"
    assert ENUM_PERF_KEY == "enum_perf"
    assert EntityMonitorStats is not None
    assert WorkerTaskPerf is not None


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
        callbacks=RunCallbacks(on_tick=_noop_on_tick),
    )
    assert result.mode == "entity_based"


def test_run_unknown_mode_raises() -> None:
    with pytest.raises(ValueError, match="unknown backtest mode"):
        BacktestEngine.run(
            "invalid",
            [],
        )


def test_entity_based_empty_jobs_returns_success() -> None:
    result = BacktestEngine.entity_based.run([])
    assert isinstance(result, BacktestEngine.RunResult)
    assert result.mode == "entity_based"
    assert result.success is True
    assert result.total_jobs == 0


def test_slice_based_empty_jobs_returns_success() -> None:
    result = BacktestEngine.slice_based.run([])
    assert isinstance(result, BacktestEngine.RunResult)
    assert result.mode == "slice_based"
    assert result.success is True
    assert result.total_jobs == 0


def test_job_lifecycle_task_start_and_complete() -> None:
    phases: list[str] = []

    def on_task_start(context: JobContext) -> str:
        phases.append("init")
        return "session"

    def on_task_complete(context: JobContext) -> None:
        phases.append("release")
        assert context.init == "session"

    def execute(context: JobContext) -> dict:
        phases.append("execute")
        assert context.init == "session"
        return {"success": True}

    from core.modules.backtest_engine.core.shared.job_lifecycle import JobLifecycle

    ctx = JobContext(job_id="j1", payload={"entity_id": "000001.SZ"})
    JobLifecycle.run(
        execute,
        ctx,
        on_task_start=on_task_start,
        on_task_complete=on_task_complete,
    )
    assert phases == ["init", "execute", "release"]


def test_run_callbacks_forward_on_receive_task_result() -> None:
    seen: list[str] = []

    def on_receive_task_result(report, progress) -> None:
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
        hook = kwargs.get("on_receive_task_result")
        if hook is not None:
            hook(
                JobReport(job_id="job-1", success=True),
                RunProgress(finished=1, total=1, ok=1, fail=0),
            )
        return mock_result

    with patch.object(EntityExecutePipeline, "run", fake_run):
        with patch.object(Timeline, "validate_window", side_effect=lambda s, e: (s, e)):
            BacktestEngine.entity_based.run(
                jobs,
                start="20240102",
                end="20240102",
                timeline=["20240102"],
                task_name="demo",
                callbacks=RunCallbacks(on_receive_task_result=on_receive_task_result),
            )

    assert seen == ["job-1"]


def test_timeline_worker_execute_wires_on_tick() -> None:
    from core.modules.backtest_engine.core.timeline.timeline import TimelineWorkerExecute

    worker = TimelineWorkerExecute()
    assert worker.callbacks.on_tick is None

    worker_tick = TimelineWorkerExecute(RunCallbacks(on_tick=_noop_on_tick))
    assert worker_tick.callbacks.on_tick is _noop_on_tick


def test_idle_on_tick_warns_once(caplog) -> None:
    import logging

    from core.modules.backtest_engine.core.timeline import timeline as timeline_mod

    timeline_mod._idle_tick_warned = False
    ctx = JobContext(job_id="j1", payload={})
    with caplog.at_level(logging.WARNING):
        Timeline._dispatch_tick(ctx, "20240102", 0, on_tick=None)
        Timeline._dispatch_tick(ctx, "20240103", 1, on_tick=None)
    warnings = [r for r in caplog.records if "on_tick 未提供" in r.getMessage()]
    assert len(warnings) == 1
    timeline_mod._idle_tick_warned = False


def test_timeline_drive_tick_order() -> None:
    events: list[str] = []
    ctx = JobContext(job_id="j1", payload={})

    def on_tick(job_context, point, index):
        _ = job_context
        events.append(f"tick:{point}:{index}")

    result = Timeline.drive(
        ctx,
        Timeline.from_points(
            ["20240101", "20240102", "20240103", "20240110"],
            start="20240102",
            end="20240103",
        ),
        on_tick=on_tick,
    )
    assert result == {"success": True}
    assert events == [
        "tick:20240102:0",
        "tick:20240103:1",
    ]


def test_entity_based_allows_missing_on_tick() -> None:
    result = BacktestEngine.entity_based.run([], performance={"max_workers": 1})
    assert result.success is True
    assert result.total_jobs == 0
