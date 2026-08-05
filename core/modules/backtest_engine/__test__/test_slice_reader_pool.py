"""Unit tests for SliceReaderPool (sync + multiprocess prefetch)."""
from __future__ import annotations

from concurrent.futures import Future
from unittest.mock import MagicMock, patch

from core.modules.backtest_engine.core.schedule.slice_based.reader_pool import (
    SliceReaderPool,
    SliceWindowKey,
)


def test_payload_for_reader_strips_hooks() -> None:
    out = SliceReaderPool.payload_for_reader(
        {
            "entity_specified": [{"id": "a"}],
            "entity_ids": ["a"],
            "entity_shared": {"k": {"start": "1", "end": "2"}},
            "_engine_on_execute_unit_done": lambda x: None,
            "shm_info": {"shm_name": "x"},
        }
    )
    assert set(out.keys()) == {"entity_specified", "entity_ids", "entity_shared"}
    assert "_engine_on_execute_unit_done" not in out


def test_sync_load_when_readers_zero() -> None:
    pool = SliceReaderPool(reader_workers=0, queue_depth=0)
    with patch.object(
        SliceReaderPool,
        "_load_sync",
        return_value={"k": "c"},
    ) as sync:
        out = pool.load_window({"entity_ids": ["a"]}, start="20240101", end="20240110")
    assert out == {"k": "c"}
    sync.assert_called_once()
    pool.shutdown()


def test_prefetch_noop_when_queue_zero() -> None:
    pool = SliceReaderPool(reader_workers=2, queue_depth=0)
    assert pool.prefetch({"entity_ids": []}, start="a", end="b") is False
    pool.shutdown()


def test_prefetch_and_load_from_ready_queue() -> None:
    pool = SliceReaderPool(reader_workers=2, queue_depth=2)
    fake_exec = MagicMock()
    fut: Future = Future()
    fut.set_result(
        {
            "entity_contracts_wire": {
                "kline": {"data": {"a": [{"date": "20240101"}]}, "runtime": {}}
            },
            "load_sec": 0.12,
            "start": "20240101",
            "end": "20240120",
        }
    )
    fake_exec.submit.return_value = fut

    fake_contract = MagicMock()
    with patch(
        "core.modules.backtest_engine.core.schedule.slice_based.reader_pool.ProcessPoolExecutor",
        return_value=fake_exec,
    ), patch.object(
        SliceReaderPool,
        "_contracts_from_wire",
        return_value={"kline": fake_contract},
    ):
        assert pool.prefetch(
            {"entity_specified": [], "entity_shared": {}},
            start="20240101",
            end="20240120",
        )
        assert pool.ready_count() == 1
        out = pool.load_window(
            {"entity_specified": [], "entity_shared": {}},
            start="20240101",
            end="20240120",
        )
    assert out == {"kline": fake_contract}
    pool.shutdown()


def test_contracts_wire_roundtrip_preserves_data() -> None:
    contract = MagicMock()
    contract.data = {"e1": [{"date": "20240102", "close": 1.0}]}
    contract.runtime = MagicMock()
    with patch.object(
        SliceReaderPool,
        "_runtime_to_dict",
        return_value={"entity_ids": ["e1"], "start": "20240101", "end": "20240110"},
    ):
        wire = SliceReaderPool._contracts_to_wire({"stock.kline.daily": contract})

    rebuilt = MagicMock()
    with patch(
        "core.modules.data_contract.ContractIssuer.issue",
        return_value=rebuilt,
    ) as issue:
        out = SliceReaderPool._contracts_from_wire(wire)

    assert out["stock.kline.daily"] is rebuilt
    assert rebuilt.data == contract.data
    assert rebuilt.is_loaded is True
    assert issue.call_args.kwargs["fill_in_data"] is False
    assert issue.call_args.kwargs["entity_ids"] == ["e1"]


def test_from_plan_reads_preload_depth() -> None:
    plan = MagicMock()
    plan.reader_workers = 3
    plan.preload_depth = 4
    plan.queue_capacity = 99
    pool = SliceReaderPool.from_plan(plan)
    assert pool.reader_workers == 3
    assert pool.queue_depth == 4


def test_window_key_orders_bounds() -> None:
    key = SliceReaderPool.window_key("20240201", "20240101")
    assert key == SliceWindowKey(start="20240101", end="20240201")
