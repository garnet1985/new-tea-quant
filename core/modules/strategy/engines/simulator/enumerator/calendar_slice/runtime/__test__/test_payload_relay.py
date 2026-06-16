"""Payload relay: out-of-order readers → ordered compute queue."""
import queue
import threading
from unittest.mock import MagicMock

from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.messages import (
    LaneError,
    SlicePayload,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.payload_relay import (
    relay_payloads_in_order,
)


def _sample_payload(slice_index: int) -> SlicePayload:
    return SlicePayload(
        slice_id=f"slice_{slice_index}",
        slice_index=slice_index,
        window_start="20240101",
        window_end="20240131",
        open_dates=("20240101",),
        batch_transfer={},
        load_elapsed_ms=1.0,
    )


def test_relay_payloads_reorders_by_slice_index():
    reader_out_q: queue.Queue = queue.Queue()
    payload_q: queue.Queue = queue.Queue()
    stop_event = threading.Event()
    errors: list[LaneError] = []

    reader_out_q.put(_sample_payload(1))
    reader_out_q.put(_sample_payload(0))
    stop_event.set()

    relay_payloads_in_order(
        reader_out_q=reader_out_q,
        payload_q=payload_q,
        slice_count=2,
        stop_event=stop_event,
        errors=errors,
    )

    assert errors == []
    first = payload_q.get_nowait()
    second = payload_q.get_nowait()
    assert first.slice_index == 0
    assert second.slice_index == 1


def test_drive_slices_multi_reader_shutdown_count():
    from unittest.mock import MagicMock, patch

    from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.messages import (
        SHUTDOWN,
        FinalizeDone,
        SliceDone,
    )
    from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.orchestrator import (
        CalendarSliceProcessOrchestrator,
    )
    from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.settings import (
        CalendarSliceRuntimeSettings,
    )
    from core.modules.strategy.engines.simulator.enumerator.calendar_slice.slice_plan import (
        CalendarSliceDescriptor,
    )
    from core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.__test__.test_orchestrator import (
        _sample_plan,
    )

    payload = {
        "stock_ids": ["000001.SZ"],
        "start_date": "20240101",
        "end_date": "20240131",
        "slice_open_days": 63,
        "settings": {
            "data": {"min_required_records": 100},
            "enumerator": {"calendar_slice": {"reader_workers": 2}},
        },
    }
    assert CalendarSliceRuntimeSettings.from_job_payload(payload).reader_workers == 2

    orch = CalendarSliceProcessOrchestrator(payload)
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

    with patch(
        "core.modules.strategy.engines.simulator.enumerator.calendar_slice.runtime.orchestrator.job_tree_rss_mb",
        return_value=500.0,
    ):
        result = orch._drive_slices(
            slices=slices,
            plan=_sample_plan(reader_workers=2),
            reader_cmd_q=reader_cmd_q,
            payload_q=payload_q,
            done_q=done_q,
            relay=None,
            child_pids=(),
        )

    assert result["success"] is True
    shutdown_calls = [c.args[0] for c in reader_cmd_q.put.call_args_list if c.args]
    assert shutdown_calls.count(SHUTDOWN) == 2
    payload_q.put.assert_any_call(SHUTDOWN)
