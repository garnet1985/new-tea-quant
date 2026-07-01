"""Tag calendar_slice orchestrator：按 slice 流式 tag_values。"""
from __future__ import annotations

from unittest.mock import MagicMock

from core.modules.strategy_legacy.engines.simulator.enumerator.calendar_sliced.runtime.messages import (
    FinalizeDone,
    SliceDone,
)
from core.modules.tag.engines.sliced.runtime.orchestrator import TagCalendarSliceOrchestrator


def test_drive_slices_invokes_on_slice_tag_values():
    job_payload = {
        "entity_ids": ["000001"],
        "slice_open_days": 10,
        "backtest_calendar": {"open_dates": ["20240102", "20240103"]},
    }
    collected: list[list] = []

    orch = TagCalendarSliceOrchestrator(
        job_payload,
        on_slice_tag_values=lambda rows: collected.append(list(rows)),
    )
    plan = MagicMock()
    plan.ahead_limit = 1
    plan.reader_workers = 1
    plan.record_slice = MagicMock()
    plan.refine_from_timings = MagicMock()
    plan.adjust_preload_after_slice = MagicMock()
    plan.to_dict = MagicMock(return_value={})

    slices = [
        MagicMock(slice_id="slice_0", slice_index=0, window_start="20240102"),
        MagicMock(slice_id="slice_1", slice_index=1, window_start="20240103"),
    ]
    done_q = MagicMock()
    done_q.get.side_effect = [
        SliceDone(
            slice_index=0,
            slice_id="slice_0",
            tag_values=({"entity_id": "000001", "as_of_date": "20240102"},),
        ),
        SliceDone(slice_index=1, slice_id="slice_1", tag_values=()),
        FinalizeDone(stock_results=[{"success": True, "errors": []}]),
    ]

    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "core.modules.tag.engines.sliced.runtime.orchestrator.job_tree_rss_mb",
        return_value=100.0,
    ):
        result = orch._drive_slices(
            slices=slices,
            plan=plan,
            reader_cmd_q=MagicMock(),
            payload_q=MagicMock(),
            done_q=done_q,
            relay=None,
            child_pids=(),
        )

    assert len(collected) == 1
    assert collected[0][0]["as_of_date"] == "20240102"
    assert result["tag_values"] == []
    assert result["total_tags"] == 1


def test_drive_slices_legacy_bulk_when_no_callback():
    job_payload = {"entity_ids": ["000001"], "slice_open_days": 10}
    orch = TagCalendarSliceOrchestrator(job_payload)
    plan = MagicMock()
    plan.ahead_limit = 1
    plan.reader_workers = 1
    plan.record_slice = MagicMock()
    plan.refine_from_timings = MagicMock()
    plan.adjust_preload_after_slice = MagicMock()
    plan.to_dict = MagicMock(return_value={})

    slices = [MagicMock(slice_id="slice_0", slice_index=0, window_start="20240102")]
    done_q = MagicMock()
    row = {"entity_id": "000001", "as_of_date": "20240102"}
    done_q.get.side_effect = [
        SliceDone(slice_index=0, slice_id="slice_0", tag_values=(row,)),
        FinalizeDone(stock_results=[{"success": True, "errors": []}]),
    ]

    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "core.modules.tag.engines.sliced.runtime.orchestrator.job_tree_rss_mb",
        return_value=100.0,
    ):
        result = orch._drive_slices(
            slices=slices,
            plan=plan,
            reader_cmd_q=MagicMock(),
            payload_q=MagicMock(),
            done_q=done_q,
            relay=None,
            child_pids=(),
        )

    assert result["tag_values"] == [row]
    assert result["total_tags"] == 1
