
def test_format_calendar_slice_plan_line():
    from core.modules.strategy.engines.simulator.enumerator.shared.progress_cli import (
        format_calendar_slice_plan_line,
    )

    line = format_calendar_slice_plan_line(
        {
            "slice_open_days": 63,
            "reader_workers": 4,
            "current_preload_depth": 3,
            "ideal_preload_ceiling": 4,
            "queue_capacity": 4,
            "memory_budget_mb": 9023.6,
            "mb_per_slice": 420.0,
        }
    )
    assert "片宽=63" in line
    assert "preload=3/4" in line
    assert "payload≈" in line
