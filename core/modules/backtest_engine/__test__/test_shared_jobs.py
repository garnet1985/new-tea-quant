"""BacktestEngine shared job contract."""
from __future__ import annotations

import pytest

from core.modules.backtest_engine.core.shared.jobs import BacktestJob


def test_from_dict_accepts_contract() -> None:
    job = BacktestJob.from_dict({"id": "000001.SZ", "payload": {"stock_id": "000001.SZ"}})
    assert job.id == "000001.SZ"
    assert job.payload == {"stock_id": "000001.SZ"}


def test_validate_many_accepts_contract() -> None:
    BacktestJob.validate_many([{"id": "000001.SZ", "payload": {"stock_id": "000001.SZ"}}])


def test_validate_many_entity_based_requires_entity_key() -> None:
    with pytest.raises(ValueError, match="entity_based payload"):
        BacktestJob.validate_many(
            [{"id": "000001.SZ", "payload": {"foo": "bar"}}],
            mode="entity_based",
        )


def test_validate_many_entity_based_accepts_batch_jobs() -> None:
    BacktestJob.validate_many(
        [{"id": "batch_0", "payload": {"jobs": [{"id": "000001.SZ", "payload": {}}]}}],
        mode="entity_based",
    )


def test_validate_many_slice_based_requires_open_dates() -> None:
    with pytest.raises(ValueError, match="open_dates"):
        BacktestJob.validate_many(
            [{"id": "bulk", "payload": {"entity_ids": ["000001.SZ"]}}],
            mode="slice_based",
        )


def test_validate_many_slice_based_accepts_bulk_job() -> None:
    BacktestJob.validate_many(
        [
            {
                "id": "bulk",
                "payload": {
                    "entity_ids": ["000001.SZ"],
                    "open_dates": ["20240101"],
                },
            }
        ],
        mode="slice_based",
    )


def test_from_dict_rejects_flat_row() -> None:
    with pytest.raises(ValueError, match="BacktestEngine job"):
        BacktestJob.from_dict({"stock_id": "000001.SZ"})


def test_batch_payloads_unwraps_payloads() -> None:
    rows = BacktestJob.batch_payloads(
        [
            {"id": "000001.SZ", "payload": {"stock_id": "000001.SZ"}},
            {"id": "000002.SZ", "payload": {"stock_id": "000002.SZ"}},
        ]
    )
    assert rows == [{"stock_id": "000001.SZ"}, {"stock_id": "000002.SZ"}]


def test_to_dict_round_trip() -> None:
    job_dict = BacktestJob(id="000001.SZ", payload={"stock_id": "000001.SZ"}).to_dict()
    assert BacktestJob.from_dict(job_dict).payload == {"stock_id": "000001.SZ"}


def test_normalize_mode_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="unknown backtest mode"):
        BacktestJob._normalize_mode("timeline")
