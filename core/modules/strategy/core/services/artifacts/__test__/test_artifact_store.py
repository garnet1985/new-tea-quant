"""ArtifactStore：allocate / 读表 / 缓存 / prune / 子类分发。"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import (
    RUNTIME_ENV_FILE,
    ArtifactStore,
    EntityInvestmentCsv,
    EnumerateStore,
    InvestmentRow,
    PortfolioStore,
    PriceFactorStore,
)

pytestmark = pytest.mark.force_run


@pytest.fixture(autouse=True)
def _clear_store_cache():
    ArtifactStore.clear_cache()
    yield
    ArtifactStore.clear_cache()


def test_at_returns_subclass_and_same_instance(tmp_path: Path) -> None:
    a = ArtifactStore.at(tmp_path, kind=SimulateKind.ENUMERATE, version_id="1")
    b = ArtifactStore.at(tmp_path, kind="enum", version_id="1")
    c = EnumerateStore.at(tmp_path, version_id="1")
    assert isinstance(a, EnumerateStore)
    assert a is b is c


def test_parse_kind_rejects_capital() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        ArtifactStore.parse_kind("capital")


def test_write_and_read_investments(tmp_path: Path) -> None:
    store = EnumerateStore.at(tmp_path, version_id="1")
    table = EntityInvestmentCsv(
        entity_id="000001.SZ",
        rows=[
            InvestmentRow(
                investment_id="1",
                trigger_date="20240102",
                lifecycle="complete",
            )
        ],
    )
    store.write_investments(table)
    ArtifactStore.clear_cache()
    loaded = EnumerateStore.at(tmp_path).investments("000001.SZ")
    assert [row.investment_id for row in loaded.rows] == ["1"]
    assert store.list_investment_entities() == ["000001.SZ"]


def test_open_reads_runtime(tmp_path: Path) -> None:
    store = EnumerateStore.at(tmp_path, version_id="9")
    store.write_text_lines("entity_ids", ["000001.SZ"])
    store.write_json(
        "runtime_env",
        {
            "strategy_key": "demo",
            "period": {"start_date": "20240102", "end_date": "20240131"},
            "market_profile": "china_a_stock",
            "settings": {"effective_settings": {"x": 1}},
        },
    )
    ArtifactStore.clear_cache()
    opened = EnumerateStore.open(tmp_path, version_id="9")
    assert opened.version_id == "9"
    assert opened.entity_ids == ["000001.SZ"]
    assert opened.start_date == "20240102"
    assert opened.runtime.strategy_key == "demo"
    assert opened.has_runtime_env()
    assert (tmp_path / RUNTIME_ENV_FILE).is_file()


def test_prune_root_keeps_newest(tmp_path: Path) -> None:
    root = tmp_path / "enum"
    for i in range(1, 5):
        (root / str(i)).mkdir(parents=True)
    deleted = ArtifactStore.prune_root(root, max_versions=2)
    assert deleted == 2
    assert sorted(p.name for p in root.iterdir()) == ["3", "4"]


def test_allocate_increments_and_prunes(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "portfolio"
    monkeypatch.setattr(
        PortfolioStore,
        "simulation_root",
        classmethod(lambda cls, folder, kind=None: root),
    )
    ids = []
    for _ in range(5):
        store = PortfolioStore.allocate(
            tmp_path,
            strategy_id="demo/s",
            max_versions=3,
        )
        ids.append(int(store.version_id))
    assert ids == [1, 2, 3, 4, 5]
    remaining = sorted(
        int(p.name) for p in root.iterdir() if p.is_dir() and p.name.isdigit()
    )
    assert remaining == [3, 4, 5]


def test_latest_reads_meta(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "price"
    (root / "2").mkdir(parents=True)
    (root / "meta.json").write_text(
        '{"next_output_version": 3}', encoding="utf-8"
    )
    monkeypatch.setattr(
        PriceFactorStore,
        "simulation_root",
        classmethod(lambda cls, folder, kind=None: root),
    )
    store = PriceFactorStore.latest(tmp_path)
    assert store is not None
    assert isinstance(store, PriceFactorStore)
    assert store.version_id == "2"
    assert store.output_dir == root / "2"
