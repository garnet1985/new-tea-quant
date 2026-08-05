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
