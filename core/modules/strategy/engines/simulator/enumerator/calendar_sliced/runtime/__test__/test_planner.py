"""Runtime planner unit tests."""
from unittest.mock import patch

from core.modules.backtest_engine.core.slice_based.config import SliceConfig
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.planner import (
    build_runtime_plan,
    ideal_preload_from_timings,
    preload_depth_from_memory,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.runtime_plan import (
    CalendarSliceRuntimePlan,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.slice_plan import (
    MIN_PLANNER_SLICE_OPEN_DAYS,
    resolve_auto_slice_open_days,
    resolve_slice_width_floor,
)


def test_auto_slice_floor():
    assert resolve_slice_width_floor() == MIN_PLANNER_SLICE_OPEN_DAYS


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


def test_resolve_auto_slice_open_days():
    days = resolve_auto_slice_open_days(
        mb_per_slice=400,
        memory_budget_mb=4096,
        open_days_total=500,
    )
    assert days >= MIN_PLANNER_SLICE_OPEN_DAYS


def test_build_runtime_plan_requires_auto_slice_marker():
    try:
        build_runtime_plan({"slice_open_days": 63}, open_days_total=100)
        assert False, "expected ValueError"
    except ValueError:
        pass

    plan = build_runtime_plan({"slice_open_days": "auto"}, open_days_total=500)
    assert plan.slice_open_days >= MIN_PLANNER_SLICE_OPEN_DAYS


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


def test_runtime_plan_record_slice_uses_payload_bytes():
    plan = CalendarSliceRuntimePlan(
        slice_open_days=63,
        memory_budget_mb=4096,
        reader_workers=4,
        ideal_preload_ceiling=3,
        current_preload_depth=3,
        queue_capacity=4,
        mb_per_slice=400,
    )
    payload_bytes = 200 * 1024 * 1024
    plan.record_slice(
        slice_index=0,
        load_sec=1.0,
        compute_sec=0.5,
        rss_after_mb=5000.0,
        payload_bytes=payload_bytes,
    )
    assert 190 <= plan.mb_per_slice <= 210


def test_slice_config_calendar_slice_block():
    from unittest.mock import patch

    from core.modules.backtest_engine.core.slice_based.config import SliceConfig
    from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.settings import (
        CalendarSliceRuntimeSettings,
    )

    with patch.object(
        SliceConfig,
        "resolve_dispatch_performance",
        return_value={"reader_workers": 2, "prefetch_enabled": True, "queue_depth": "auto"},
    ):
        cfg = CalendarSliceRuntimeSettings.from_worker_config()
    assert cfg.reader_workers == 2
    assert cfg.queue_depth_raw == "auto"
    assert cfg.prefetch_enabled is True
