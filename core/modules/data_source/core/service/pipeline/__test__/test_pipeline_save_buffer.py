"""DataSourceSaveBuffer：按字节封顶，分块前只保留表。"""
import pandas as pd

from core.modules.data_source.core.service.pipeline.frame_mapping import frame_nbytes
from core.modules.data_source.core.service.pipeline.save_buffer import DataSourceSaveBuffer
from core.modules.data_source.core.service.pipeline.save_memory_budget import SaveMemoryBudget


def _budget(budget_bytes: int) -> SaveMemoryBudget:
    return SaveMemoryBudget(budget_bytes=budget_bytes, cpu_cap=2, write_reserve_bytes=0)


def test_flushes_before_accepting_a_frame_that_would_overflow():
    saved = []
    payload = "x" * 2000
    frame = pd.DataFrame({"x": [payload, payload, payload]})
    size = frame_nbytes(frame)
    buf = DataSourceSaveBuffer(
        context={"data_manager": None},
        budget=_budget(size * 2 + 1),
        to_frames=lambda _ctx, _bundle, result: [result["frame"]],
        save_frames=lambda _ctx, frames: saved.append(list(frames)),
    )
    buf.add(object(), {"frame": frame})
    assert saved == []
    buf.add(object(), {"frame": pd.DataFrame({"x": [payload, payload, payload]})})
    assert len(saved) == 1
    assert list(saved[0][0]["x"]) == [payload, payload, payload]
    buf.flush_remaining()
    assert len(saved) == 2


def test_empty_frame_is_not_buffered():
    saved = []
    buf = DataSourceSaveBuffer(
        context={"data_manager": None},
        budget=_budget(100),
        to_frames=lambda _ctx, _bundle, _result: [pd.DataFrame()],
        save_frames=lambda _ctx, frames: saved.append(frames),
    )
    buf.add(object(), {})
    buf.flush_remaining()
    assert saved == []
