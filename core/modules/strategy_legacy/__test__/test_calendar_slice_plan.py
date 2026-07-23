#!/usr/bin/env python3
"""Calendar slice planning unit tests."""

from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.slice_plan import (
    MIN_PLANNER_SLICE_OPEN_DAYS,
    clamp_resolved_slice_open_days,
    is_first_open_of_month,
    plan_calendar_slices,
    resolve_auto_slice_open_days,
    resolve_slice_width_floor,
)


class TestCalendarSlicePlan:
    def test_plan_slices_chunks_open_dates(self):
        open_dates = [f"202401{d:02d}" for d in range(1, 11)]
        slices = plan_calendar_slices(open_dates, slice_open_days=4)
        assert len(slices) == 3
        assert slices[0].slice_id == "slice_0"
        assert slices[0].open_dates == tuple(open_dates[:4])
        assert slices[0].window_start == open_dates[0]
        assert slices[0].window_end == open_dates[3]
        assert slices[2].open_dates == tuple(open_dates[8:])

    def test_resolve_slice_width_floor_default(self):
        assert resolve_slice_width_floor() == MIN_PLANNER_SLICE_OPEN_DAYS

    def test_resolve_auto_slice_open_days(self):
        days = resolve_auto_slice_open_days(
            mb_per_slice=400,
            memory_budget_mb=4096,
            open_days_total=500,
        )
        assert days >= MIN_PLANNER_SLICE_OPEN_DAYS

    def test_clamp_resolved_slice_open_days(self):
        assert clamp_resolved_slice_open_days(500) == 252
        assert clamp_resolved_slice_open_days(3) == MIN_PLANNER_SLICE_OPEN_DAYS

    def test_is_first_open_of_month(self):
        dates = ["20240129", "20240130", "20240131", "20240201", "20240202"]
        assert is_first_open_of_month("20240129", dates) is True
        assert is_first_open_of_month("20240130", dates) is False
        assert is_first_open_of_month("20240201", dates) is True

    def test_is_last_open_of_month(self):
        from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.slice_plan import (
            is_last_open_of_month,
        )

        dates = ["20240129", "20240130", "20240131", "20240201", "20240202"]
        assert is_last_open_of_month("20240131", dates) is True
        assert is_last_open_of_month("20240130", dates) is False
        assert is_last_open_of_month("20240202", dates) is True

    def test_is_first_open_of_year(self):
        from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.slice_plan import (
            is_first_open_of_year,
            is_last_open_of_year,
        )

        dates = ["20231229", "20240102", "20240103", "20241230", "20241231", "20250102", "20250103"]
        assert is_first_open_of_year("20240102", dates) is True
        assert is_first_open_of_year("20240103", dates) is False
        assert is_last_open_of_year("20241231", dates) is True
        assert is_last_open_of_year("20250102", dates) is False
