"""price_factor.load_enum_data：只读 runtime + entity_ids。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.modules.strategy.core.engines.shared.services.simulation_input.artifact_paths import (
    ENTITY_IDS_FILE,
    RUNTIME_ENV_FILE,
    ReportPaths,
)
from core.modules.strategy.core.engines.shared.services.simulation_input.stock_investments import (
    InvestmentRow,
    StockInvestments,
)
from core.modules.strategy.core.engines.shared.services.simulation_input.enum_loader import load_enum_version

pytestmark = pytest.mark.force_run


def _write_runtime(
    output_dir: Path,
    *,
    entity_ids: list[str],
    start: str = "20240102",
    end: str = "20240131",
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ENTITY_IDS_FILE).write_text(
        "\n".join(entity_ids) + ("\n" if entity_ids else ""),
        encoding="utf-8",
    )
    payload = {
        "strategy_key": "demo",
        "version_id": 1,
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


def test_load_enum_version_reads_runtime_and_entity_ids(tmp_path: Path) -> None:
    _write_runtime(tmp_path, entity_ids=["000001.SZ", "000002.SZ"])
    # entities CSV 存在也不应被主进程加载进 EnumVersionData
    StockInvestments(
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
    ).save(tmp_path)

    data = load_enum_version(tmp_path, "7")

    assert data.version_id == "7"
    assert data.output_dir == tmp_path
    assert data.entity_ids == ["000001.SZ", "000002.SZ"]
    assert data.start_date == "20240102"
    assert data.end_date == "20240131"


def test_load_enum_version_empty_entity_ids(tmp_path: Path) -> None:
    _write_runtime(tmp_path, entity_ids=[])
    ReportPaths.entities_dir(tmp_path).mkdir(parents=True, exist_ok=True)
    data = load_enum_version(tmp_path, "1")
    assert data.entity_ids == []


def test_load_enum_version_requires_runtime_env(tmp_path: Path) -> None:
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / ENTITY_IDS_FILE).write_text("000001.SZ\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        load_enum_version(tmp_path, "1")
