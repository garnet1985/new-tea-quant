"""Unit tests for SliceOrchestrator (BE-owned window / lookback / progress)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.modules.backtest_engine.core.schedule.slice_based.orchestrator import (
    SliceOrchestrator,
    SliceScheduleState,
)
from core.modules.backtest_engine.core.schedule.slice_based.reader_pool import (
    SliceReaderPool,
)

pytestmark = pytest.mark.force_run


def test_split_windows_covers_all_points() -> None:
    assert SliceOrchestrator.split_windows(0, 20) == []
    assert SliceOrchestrator.split_windows(10, 20) == [(0, 9)]
    assert SliceOrchestrator.split_windows(45, 20) == [(0, 19), (20, 39), (40, 44)]


def test_lookback_start_index() -> None:
    assert SliceOrchestrator.lookback_start_index(0, 5) == 0
    assert SliceOrchestrator.lookback_start_index(10, 5) == 6


def test_complete_window_reports_progress_and_releases_contracts() -> None:
    calls: list[int] = []
    pool = SliceReaderPool(reader_workers=0, queue_depth=0)
    sched = SliceScheduleState(
        points=[f"d{i}" for i in range(60)],
        slice_open_days=20,
        min_required=5,
        head_sample_slices=0,
        memory_budget_mb=0.0,
        reader_pool=pool,
        slice_index=0,
    )
    job_context = MagicMock()
    job_context.payload = {"_engine_on_execute_unit_done": calls.append}
    job_context.init = {"entity_contracts": {"k": object()}}

    with patch.object(SliceOrchestrator, "_prefetch_ahead"):
        SliceOrchestrator._complete_window(job_context, sched, end_idx=19)

    assert calls == [1]
    assert job_context.init["entity_contracts"] == {}


def test_load_window_uses_lookback_and_counts() -> None:
    points = [f"202401{i:02d}" for i in range(1, 31)]
    contracts = {"k": object()}
    pool = MagicMock()
    pool.load_window.return_value = contracts
    pool.ready_count.return_value = 0
    pool.loading_count.return_value = 0
    sched = SliceScheduleState(
        points=points,
        slice_open_days=10,
        min_required=5,
        head_sample_slices=0,
        memory_budget_mb=0.0,
        reader_pool=pool,
        slice_index=1,
    )
    job_context = MagicMock()
    job_context.payload = {"entity_ids": ["a"]}
    job_context.init = {}

    SliceOrchestrator._load_window(job_context, sched, start_idx=10, end_idx=19)

    assert sched.per_entity_load_count == 1
    assert job_context.init["entity_contracts"] is contracts
    kwargs = pool.load_window.call_args.kwargs
    assert kwargs["start"] == points[6]
    assert kwargs["end"] == points[19]


def test_run_invokes_task_hooks_per_slice_and_merges_complete() -> None:
    from core.modules.backtest_engine.core.shared.types import JobContext, RunCallbacks

    points = ["d1", "d2", "d3", "d4"]
    timeline = MagicMock()
    timeline.clipped.return_value = MagicMock(points=points)
    pool = MagicMock()
    pool.reader_workers = 0
    pool.queue_depth = 0
    pool.load_window.return_value = {"e": object()}

    phases: list[str] = []
    task_meta: list[tuple[int, int]] = []

    def on_task_start(ctx: JobContext) -> dict:
        phases.append("start")
        return {"entity_contracts": ctx.init.get("entity_contracts", {}), "global_data": {}}

    def on_task_complete(ctx: JobContext) -> dict:
        phases.append("complete")
        task_meta.append((ctx.init["_task_index"], ctx.init["_task_total"]))
        return {"opportunities_count": ctx.init["_task_index"]}

    def on_tick(ctx: JobContext, point: str, index: int) -> None:
        phases.append(f"tick:{point}")

    job_context = JobContext(
        job_id="j1",
        payload={"_slice_plan": {"slice_open_days": 2, "reader_workers": 0, "preload_depth": 0}},
        init={},
    )
    callbacks = RunCallbacks(
        on_task_start=on_task_start,
        on_task_complete=on_task_complete,
        on_tick=on_tick,
    )

    with patch.object(SliceOrchestrator, "_reader_pool", return_value=pool), patch(
        "core.modules.backtest_engine.core.schedule.slice_based.orchestrator.Timeline.read_for_job",
        return_value=timeline,
    ), patch.object(
        SliceOrchestrator, "_process_rss_mb", side_effect=[40.0, 50.0, 55.0, 60.0]
    ) as rss:
        result = SliceOrchestrator.run(job_context, callbacks=callbacks)

    assert result["success"] is True
    assert result["opportunities_count"] == 2
    # Prep on_task_start (globals) once, then per-slice start/complete.
    assert phases == [
        "start",
        "start",
        "tick:d1",
        "tick:d2",
        "complete",
        "start",
        "tick:d3",
        "tick:d4",
        "complete",
    ]
    assert task_meta == [(1, 2), (2, 2)]
    # Baseline taken after prep start (first rss call), before window loads.
    assert rss.call_count >= 1


def test_baseline_rss_taken_after_prep_task_start() -> None:
    """payload_mb baseline excludes globals: RSS sampled after prep on_task_start."""
    from core.modules.backtest_engine.core.shared.types import JobContext, RunCallbacks

    points = ["d1", "d2"]
    timeline = MagicMock()
    timeline.clipped.return_value = MagicMock(points=points)
    pool = MagicMock()
    pool.reader_workers = 0
    pool.queue_depth = 0
    pool.load_window.return_value = {"e": object()}

    rss_calls: list[float] = []

    def on_task_start(ctx: JobContext) -> dict:
        init = ctx.init if isinstance(ctx.init, dict) else {}
        if init.get("_ready"):
            return init
        return {
            "entity_contracts": {},
            "global_data": {"g": 1},
            "_ready": True,
        }

    job_context = JobContext(
        job_id="j1",
        payload={
            "_slice_plan": {
                "slice_open_days": 2,
                "reader_workers": 0,
                "preload_depth": 0,
            },
            "_slice_head_sample_slices": 1,
        },
        init={},
    )

    def fake_rss() -> float:
        ready = isinstance(job_context.init, dict) and job_context.init.get("_ready")
        val = 100.0 if ready else 10.0
        if isinstance(job_context.init, dict) and job_context.init.get("entity_contracts"):
            val = 130.0
        rss_calls.append(val)
        return val

    with patch.object(SliceOrchestrator, "_reader_pool", return_value=pool), patch(
        "core.modules.backtest_engine.core.schedule.slice_based.orchestrator.Timeline.read_for_job",
        return_value=timeline,
    ), patch.object(SliceOrchestrator, "_process_rss_mb", side_effect=fake_rss), patch.object(
        SliceOrchestrator, "_prefetch_ahead"
    ):
        SliceOrchestrator.run(
            job_context,
            callbacks=RunCallbacks(on_task_start=on_task_start),
        )

    assert rss_calls[0] == 100.0
