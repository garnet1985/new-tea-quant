"""BacktestEngine shared job contract."""
from __future__ import annotations

import pytest

from core.modules.backtest_engine.core.shared.modes import BacktestMode
from core.modules.backtest_engine.core.shared.jobs import BacktestJob


def test_from_dict_accepts_contract() -> None:
    job = BacktestJob.from_dict(
        {"id": "000001.SZ", "payload": {"entity_specified": [{"id": "000001.SZ"}]}}
    )
    assert job.id == "000001.SZ"
    assert job.payload == {"entity_specified": [{"id": "000001.SZ"}]}


def test_validate_many_accepts_contract() -> None:
    BacktestJob.validate_many(
        [{"id": "000001.SZ", "payload": {"entity_specified": [{"id": "000001.SZ"}]}}]
    )


def test_validate_many_entity_based_requires_entity_key() -> None:
    with pytest.raises(ValueError, match="entity_based payload"):
        BacktestJob.validate_many(
            [{"id": "000001.SZ", "payload": {"foo": "bar"}}],
            mode=BacktestMode.ENTITY_BASED,
        )


def test_validate_many_entity_based_rejects_aliases() -> None:
    with pytest.raises(ValueError, match="entity_specified"):
        BacktestJob.validate_many(
            [{"id": "000001.SZ", "payload": {"entity_id": "000001.SZ"}}],
            mode=BacktestMode.ENTITY_BASED,
        )


def test_validate_many_entity_based_accepts_bundle_jobs() -> None:
    BacktestJob.validate_many(
        [
            {
                "id": "batch_0",
                "payload": {
                    "entity_specified": [{"id": "000001.SZ"}, {"id": "000002.SZ"}],
                },
            }
        ],
        mode=BacktestMode.ENTITY_BASED,
    )


def test_validate_many_slice_based_requires_point_count() -> None:
    with pytest.raises(ValueError, match="timeline_point_count"):
        BacktestJob.validate_many(
            [{"id": "bulk", "payload": {"entity_ids": ["000001.SZ"]}}],
            mode=BacktestMode.SLICE_BASED,
        )


def test_validate_many_slice_based_rejects_stock_ids_alias() -> None:
    with pytest.raises(ValueError, match="entity_ids"):
        BacktestJob.validate_many(
            [
                {
                    "id": "bulk",
                    "payload": {
                        "stock_ids": ["000001.SZ"],
                        "timeline_point_count": 1,
                    },
                }
            ],
            mode=BacktestMode.SLICE_BASED,
        )


def test_validate_many_slice_based_accepts_bulk_job() -> None:
    BacktestJob.validate_many(
        [
            {
                "id": "bulk",
                "payload": {
                    "entity_ids": ["000001.SZ"],
                    "timeline_point_count": 1,
                },
            }
        ],
        mode=BacktestMode.SLICE_BASED,
    )


def test_from_dict_rejects_flat_row() -> None:
    with pytest.raises(ValueError, match="BacktestEngine job"):
        BacktestJob.from_dict({"entity_specified": [{"id": "000001.SZ"}]})


def test_batch_payloads_unwraps_payloads() -> None:
    rows = BacktestJob.batch_payloads(
        [
            {
                "id": "000001.SZ",
                "payload": {"entity_specified": [{"id": "000001.SZ"}]},
            },
            {
                "id": "000002.SZ",
                "payload": {"entity_specified": [{"id": "000002.SZ"}]},
            },
        ]
    )
    assert rows == [
        {"entity_specified": [{"id": "000001.SZ"}]},
        {"entity_specified": [{"id": "000002.SZ"}]},
    ]


def test_to_dict_round_trip() -> None:
    job_dict = BacktestJob(
        id="000001.SZ",
        payload={"entity_specified": [{"id": "000001.SZ"}]},
    ).to_dict()
    assert BacktestJob.from_dict(job_dict).payload == {
        "entity_specified": [{"id": "000001.SZ"}]
    }


def test_normalize_mode_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="unknown backtest mode"):
        BacktestMode.normalize("timeline")
