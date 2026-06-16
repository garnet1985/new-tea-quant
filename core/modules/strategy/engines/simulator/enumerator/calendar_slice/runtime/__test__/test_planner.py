"""Runtime planner unit tests."""
from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.planner import (
    ideal_preload_from_timings,
    preload_depth_from_memory,
    resolve_slice_open_days_for_job,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.runtime_plan import (
    CalendarSliceRuntimePlan,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_slice.slice_plan import (
    MIN_PLANNER_SLICE_OPEN_DAYS,
    auto_slice_open_days_floor,
    reject_if_min_records_exceeds_max_slice,
)


def test_auto_slice_floor():
    assert auto_slice_open_days_floor(15) == MIN_PLANNER_SLICE_OPEN_DAYS
    assert auto_slice_open_days_floor(80) == 80


def test_reject_min_records_above_max():
    try:
        reject_if_min_records_exceeds_max_slice(300)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_ideal_preload_from_timings():
    assert ideal_preload_from_timings(2.0, 0.05) >= 2
    assert ideal_preload_from_timings(0.1, 0.1) >= 1


def test_preload_depth_from_memory():
    depth = preload_depth_from_memory(
        memory_budget_mb=2048,
        mb_per_slice=400,
        carry_reserve_mb=128,
        compute_reserve_mb=64,
    )
    assert depth >= 4


def test_resolve_slice_open_days_auto():
    days = resolve_slice_open_days_for_job(
        "auto",
        min_required_records=15,
        mb_per_slice=400,
        memory_budget_mb=4096,
        open_days_total=500,
    )
    assert days >= MIN_PLANNER_SLICE_OPEN_DAYS


def test_runtime_plan_adjust_preload_tight():
    plan = CalendarSliceRuntimePlan(
        slice_open_days=63,
        memory_budget_mb=1000,
        reader_workers=4,
        ideal_preload_ceiling=4,
        current_preload_depth=4,
        queue_capacity=4,
        mb_per_slice=400,
    )
    plan.adjust_preload_after_slice(job_rss_mb=950)
    assert plan.current_preload_depth < 4


def test_runtime_plan_ahead_limit_binds_preload():
    plan = CalendarSliceRuntimePlan(
        slice_open_days=63,
        memory_budget_mb=4096,
        reader_workers=4,
        ideal_preload_ceiling=3,
        current_preload_depth=3,
        queue_capacity=4,
        mb_per_slice=200,
    )
    assert plan.ahead_limit == 3
