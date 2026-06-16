"""SliceLoadRequest 与 runtime settings。"""
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.messages import (
    SliceLoadRequest,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.slice_plan import (
    CalendarSliceDescriptor,
)


def test_slice_load_request_from_descriptor():
    desc = CalendarSliceDescriptor(
        slice_id="slice_0",
        slice_index=0,
        window_start="20240101",
        window_end="20240131",
        open_dates=("20240101", "20240102"),
    )
    req = SliceLoadRequest.from_descriptor(desc, load_start="20231201")
    assert req.slice_id == "slice_0"
    assert req.load_start == "20231201"
    assert req.open_dates == ("20240101", "20240102")
