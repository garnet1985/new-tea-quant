"""BacktestEngine shared job contract."""
from __future__ import annotations

import pytest

from core.modules.backtest_engine.core.shared.jobs import BacktestJob


def test_from_wire_accepts_contract() -> None:
    job = BacktestJob.from_wire({"id": "000001.SZ", "payload": {"stock_id": "000001.SZ"}})
    assert job.id == "000001.SZ"
    assert job.payload == {"stock_id": "000001.SZ"}


def test_validate_many_accepts_contract() -> None:
    BacktestJob.validate_many([{"id": "000001.SZ", "payload": {"stock_id": "000001.SZ"}}])


def test_from_wire_rejects_flat_row() -> None:
    with pytest.raises(ValueError, match="BacktestEngine job"):
        BacktestJob.from_wire({"stock_id": "000001.SZ"})


def test_batch_payloads_unwraps_payloads() -> None:
    rows = BacktestJob.batch_payloads(
        [
            {"id": "000001.SZ", "payload": {"stock_id": "000001.SZ"}},
            {"id": "000002.SZ", "payload": {"stock_id": "000002.SZ"}},
        ]
    )
    assert rows == [{"stock_id": "000001.SZ"}, {"stock_id": "000002.SZ"}]


def test_to_wire_round_trip() -> None:
    wire = BacktestJob(id="000001.SZ", payload={"stock_id": "000001.SZ"}).to_wire()
    assert BacktestJob.from_wire(wire).payload == {"stock_id": "000001.SZ"}
