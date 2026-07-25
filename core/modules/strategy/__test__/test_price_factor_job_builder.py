"""price_factor PriceFactorJobBuilder：bundle entity ids + enum_dir。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.modules.backtest_engine.core.shared.jobs import BacktestJob
from core.modules.strategy.core.engines.shared.services.simulation_output.file_names import (
    ENTITY_IDS_FILE,
    RUNTIME_ENV_FILE,
)
from core.modules.strategy.core.engines.shared.services.simulation_output.enum_source import EnumSource
from core.modules.strategy.core.engines.price_factor.job_builder import (
    PriceFactorJobBuilder,
    PRICE_FACTOR_GLOBAL_KEY,
)

pytestmark = pytest.mark.force_run


def _write_runtime(
    output_dir: Path,
    *,
    entity_ids: list[str],
    start: str = "20240102",
    end: str = "20240110",
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ENTITY_IDS_FILE).write_text(
        "\n".join(entity_ids) + ("\n" if entity_ids else ""),
        encoding="utf-8",
    )
    payload = {
        "strategy_key": "demo/strategy",
        "strategy_path": "demo/strategy",
        "version_id": 3,
        "execution_mode": "entity_based",
        "market_profile": "china_a_stock",
        "period": {"start_date": start, "end_date": end},
        "fingerprints": {"settings": "s", "env": "e"},
        "system": {},
        "settings": {"effective_settings": {"market_profile": "china_a_stock"}},
    }
    (output_dir / RUNTIME_ENV_FILE).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_build_jobs_bundle_shape(tmp_path: Path) -> None:
    _write_runtime(tmp_path, entity_ids=["000001.SZ", "000002.SZ"])
    data = EnumSource.load(tmp_path, "3")

    jobs = PriceFactorJobBuilder.build_jobs(data)
    BacktestJob.validate_many(jobs, mode="entity_based")

    assert len(jobs) == 1
    assert jobs[0]["id"] == "price_factor_run"
    payload = jobs[0]["payload"]
    assert payload["entities_count"] == 2
    assert payload["entity_specified"] == [
        {"id": "000001.SZ"},
        {"id": "000002.SZ"},
    ]
    meta = PriceFactorJobBuilder.price_factor_meta(payload)
    assert meta["enum_output_dir"] == str(tmp_path)
    assert meta["enum_version_id"] == "3"
    assert meta["start_date"] == "20240102"
    assert meta["end_date"] == "20240110"
    assert PRICE_FACTOR_GLOBAL_KEY in payload["global"]


def test_build_jobs_empty_entity_ids(tmp_path: Path) -> None:
    _write_runtime(tmp_path, entity_ids=[])
    data = EnumSource.load(tmp_path, "1")
    assert PriceFactorJobBuilder.build_jobs(data) == []


def test_build_jobs_rejects_missing_period(tmp_path: Path) -> None:
    _write_runtime(tmp_path, entity_ids=["000001.SZ"], start="", end="")
    data = EnumSource.load(tmp_path, "1")
    with pytest.raises(ValueError, match="period"):
        PriceFactorJobBuilder.build_jobs(data)
