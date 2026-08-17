"""price_factor.load_enum_data：只读 runtime + entity_ids。"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.strategy.core.services.artifacts import (
    ENTITY_IDS_FILE,
    RUNTIME_ENV_FILE,
    EntityInvestmentCsv,
    EnumerateStore,
    InvestmentRow,
)

pytestmark = pytest.mark.force_run


def _write_runtime(
    output_dir: Path,
    *,
    entity_ids: list[str],
    start: str = "20240102",
    end: str = "20240131",
) -> None:
    store = EnumerateStore.at(output_dir)
    store.write_text_lines("entity_ids", entity_ids)
    store.write_json(
        "runtime_env",
        {
            "strategy_key": "demo",
            "version_id": 1,
            "execution_mode": "entity_based",
            "market_profile": "china_a_stock",
            "period": {"start_date": start, "end_date": end},
            "fingerprints": {"settings": "s", "env": "e"},
            "system": {},
            "settings": {"effective_settings": {"market_profile": "china_a_stock"}},
        },
    )


def test_load_enum_output_reads_runtime_and_entity_ids(tmp_path: Path) -> None:
    _write_runtime(tmp_path, entity_ids=["000001.SZ", "000002.SZ"])
    # entities CSV 存在也不应被 open 时加载
    EnumerateStore.at(tmp_path).write_investments(
        EntityInvestmentCsv(
            entity_id="000001.SZ",
            rows=[
                InvestmentRow(
                    investment_id="opp-1",
                    trigger_date="20240102",
                    entry_date="20240103",
                    entry_price=10.0,
                    lifecycle="complete",
                )
            ],
        )
    )

    data = EnumerateStore.open(tmp_path, version_id="7")

    assert data.version_id == "7"
    assert data.output_dir == tmp_path
    assert data.entity_ids == ["000001.SZ", "000002.SZ"]
    assert data.start_date == "20240102"
    assert data.end_date == "20240131"


def test_load_enum_output_empty_entity_ids(tmp_path: Path) -> None:
    _write_runtime(tmp_path, entity_ids=[])
    EnumerateStore.at(tmp_path).ensure_entities_dir()
    data = EnumerateStore.open(tmp_path, version_id="1")
    assert data.entity_ids == []


def test_load_enum_output_requires_runtime_env(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / ENTITY_IDS_FILE).write_text("000001.SZ\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        EnumerateStore.open(tmp_path, version_id="1")
    assert not (tmp_path / RUNTIME_ENV_FILE).is_file()
