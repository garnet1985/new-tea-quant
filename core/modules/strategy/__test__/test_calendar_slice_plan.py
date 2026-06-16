#!/usr/bin/env python3
"""Calendar slice planning unit tests."""

from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.slice_plan import (
    clamp_slice_open_days,
    is_first_open_of_month,
    plan_calendar_slices,
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

    def test_clamp_slice_open_days_respects_min_required_records(self):
        assert clamp_slice_open_days(3, min_required_records=100) == 100
        assert clamp_slice_open_days(500, min_required_records=20) == 252

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
