"""Orchestrator shutdown before finalize (avoid deadlock)."""
from unittest.mock import MagicMock

from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.messages import (
    SHUTDOWN,
    FinalizeDone,
    SliceDone,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.orchestrator import (
    CalendarSliceProcessOrchestrator,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_slice.slice_plan import (
    CalendarSliceDescriptor,
)


def test_drive_slices_sends_shutdown_before_waiting_finalize():
    orch = CalendarSliceProcessOrchestrator(
        {
            "stock_ids": ["000001.SZ"],
            "start_date": "20240101",
            "end_date": "20240131",
            "slice_open_days": 63,
            "settings": {"data": {"min_required_records": 100}, "enumerator": {}},
        }
    )
    slices = [
        CalendarSliceDescriptor(
            slice_id="slice_0",
            slice_index=0,
            window_start="20240101",
            window_end="20240131",
            open_dates=("20240101",),
        )
    ]
    reader_cmd_q = MagicMock()
    payload_q = MagicMock()
    done_q = MagicMock()
    done_q.get.side_effect = [
        SliceDone(slice_index=0, slice_id="slice_0"),
        FinalizeDone(stock_results=[], calendar_progress={}, performance_metrics={}),
    ]

    result = orch._drive_slices(
        slices=slices,
        reader_cmd_q=reader_cmd_q,
        payload_q=payload_q,
        done_q=done_q,
    )

    assert result["success"] is True
    reader_cmd_q.put.assert_any_call(SHUTDOWN)
    payload_q.put.assert_any_call(SHUTDOWN)
    assert done_q.get.call_count == 2
