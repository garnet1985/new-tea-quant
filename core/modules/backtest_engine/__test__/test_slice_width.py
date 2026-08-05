"""Unit tests for SliceMemoryPlanner (SOT: SLICE_BASED_ALGORITHM.md)."""
from __future__ import annotations

import pytest

from core.modules.backtest_engine.core.schedule.slice_based.slice_width import (
    SliceMemoryPlanner,
    SliceWidthError,
)


def test_assert_probe_fits_rejects_too_large_probe() -> None:
    with pytest.raises(SliceWidthError, match="探针块"):
        SliceMemoryPlanner.assert_probe_fits(budget_mb=100.0, probe_mb=50.0)


def test_resolve_initial_prefers_large_queue_then_width() -> None:
    # budget*0.8=8000; R=6 (8-1-1); N from 6→0 until width>=min_required.
    plan = SliceMemoryPlanner.resolve_initial(
        budget_mb=10_000.0,
        probe_mb=20.0,
        probe_width=20,
        cpu_count=8,
        reserve_cores=1,
        min_required=20,
    )
    assert plan.reader_workers == 6
    assert plan.min_required == 20
    assert plan.slice_open_days >= 20
    assert plan.queue_depth == plan.reader_workers
    assert plan.peak_slices == 2 + plan.queue_depth + plan.reader_workers
    assert plan.mb_per_open_day == pytest.approx(1.0)


def test_default_min_required_when_unset_or_nonpositive() -> None:
    assert SliceMemoryPlanner.default_min_required(None) == 20
    assert SliceMemoryPlanner.default_min_required(0) == 20
    assert SliceMemoryPlanner.default_min_required(5) == 5


def test_fail_when_min_required_cannot_fit_even_at_queue_zero() -> None:
    # probe fits (80 >= 2*20), but R=6 → peak_slices≥8 → width≤10 < min_required=20
    with pytest.raises(SliceWidthError, match="内存不足以支撑"):
        SliceMemoryPlanner.resolve_initial(
            budget_mb=100.0,
            probe_mb=20.0,
            probe_width=20,
            cpu_count=8,
            reserve_cores=1,
            min_required=20,
        )


def test_reader_workers_zero_on_low_core() -> None:
    assert (
        SliceMemoryPlanner.reader_workers_from_cpu(cpu_count=1, reserve_cores=1) == 0
    )
    assert (
        SliceMemoryPlanner.reader_workers_from_cpu(cpu_count=2, reserve_cores=1) == 0
    )
    assert (
        SliceMemoryPlanner.reader_workers_from_cpu(cpu_count=3, reserve_cores=1) == 1
    )


def test_resolve_from_unit_cost_matches_probe_path() -> None:
    a = SliceMemoryPlanner.resolve_from_unit_cost(
        budget_mb=5_000.0,
        mb_per_open_day=2.0,
        cpu_count=4,
        reserve_cores=1,
        min_required=20,
    )
    b = SliceMemoryPlanner.resolve_initial(
        budget_mb=5_000.0,
        probe_mb=40.0,
        probe_width=20,
        cpu_count=4,
        reserve_cores=1,
        min_required=20,
    )
    assert a == b


def test_refine_queue_depth_uses_timing_clamped_by_memory() -> None:
    # n_ideal=ceil(2/1)=2; n_max=floor(800/50 - 2 - 2)=floor(16-4)=12 → 2
    depth = SliceMemoryPlanner.refine_queue_depth(
        budget_mb=1_000.0,
        mb_per_slice=50.0,
        reader_workers=2,
        current_queue=6,
        t_load_sec=2.0,
        t_compute_sec=1.0,
    )
    assert depth == 2


def test_refine_queue_depth_memory_floor_to_zero() -> None:
    # n_max=floor(80/40 - 2 - 2)=floor(2-4)=0
    depth = SliceMemoryPlanner.refine_queue_depth(
        budget_mb=100.0,
        mb_per_slice=40.0,
        reader_workers=2,
        current_queue=4,
        t_load_sec=2.0,
        t_compute_sec=1.0,
    )
    assert depth == 0
