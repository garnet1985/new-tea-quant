"""ArtifactStore：allocate / 读表 / 缓存 / prune / 子类分发。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import (
    RUNTIME_ENV_FILE,
    ArtifactStore,
    EnumerateStore,
    PortfolioStore,
    PriceFactorStore,
)
from core.modules.strategy.core.services.artifacts.version_meta import VersionMetaStore

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


def test_write_and_list_enum_json(tmp_path: Path) -> None:
    from core.modules.strategy.core.engines.shared.enum_result_contract import (
        EnumResult,
        EnumResultsManager,
    )

    manager = EnumResultsManager.at(tmp_path)
    manager.accept(
        "000001.SZ",
        [
            EnumResult(
                investment_id="1",
                trigger_date="20240102",
                lifecycle="complete",
            )
        ],
    )
    manager.persist("000001.SZ")
    store = EnumerateStore.at(tmp_path, version_id="1")
    assert store.has_investments("000001.SZ")
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


def test_open_hydrates_runtime_from_version_archive(tmp_path: Path) -> None:
    simulations = tmp_path / "simulations"
    step_dir = simulations / "2" / "enum"
    step_dir.mkdir(parents=True)
    VersionMetaStore.write_version_archive(
        simulations,
        "2",
        full_settings={"core": {"n": 1}, "analysis": {"enabled": True}},
        effective_settings={"core": {"n": 1}},
        entity_ids=["000001.SZ"],
        start_date="20240102",
        end_date="20240131",
    )
    store = EnumerateStore.at(step_dir, version_id="2")
    store.write_json(
        "runtime_env",
        {"strategy_key": "demo", "market_profile": "china_a_stock"},
    )
    ArtifactStore.clear_cache()
    opened = EnumerateStore.open(step_dir, version_id="2")
    assert opened.entity_ids == ["000001.SZ"]
    assert opened.start_date == "20240102"
    assert opened.end_date == "20240131"
    assert opened.runtime.settings_snapshot.effective_settings == {"core": {"n": 1}}


def test_prune_drops_oldest_stale_env_group(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "simulations"
    monkeypatch.setattr(
        ArtifactStore,
        "simulations_root",
        classmethod(lambda cls, folder: root),
    )
    monkeypatch.setattr(
        ArtifactStore,
        "_delete_attribution_env",
        classmethod(lambda cls, folder, env_fp: None),
    )
    for vid, env in (("1", "old-a"), ("2", "old-a"), ("3", "old-b"), ("4", "live")):
        (root / vid).mkdir(parents=True)
        VersionMetaStore.register_version(root, vid, execute_fp="s", env_fp=env)
    out = ArtifactStore.prune(tmp_path, env_fp="live", max_stale_envs=1)
    assert out["ok"] is True
    assert out["deleted_count"] == 2
    assert out["pruned_envs"] == ["old-a"]
    remaining = sorted(
        p.name for p in root.iterdir() if p.is_dir() and p.name.isdigit()
    )
    assert remaining == ["3", "4"]


def test_prune_keeps_live_env_even_when_many_versions(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "simulations"
    monkeypatch.setattr(
        ArtifactStore,
        "simulations_root",
        classmethod(lambda cls, folder: root),
    )
    for i in range(1, 6):
        (root / str(i)).mkdir(parents=True)
        VersionMetaStore.register_version(root, str(i), execute_fp="s", env_fp="live")
    out = ArtifactStore.prune(tmp_path, env_fp="live", max_stale_envs=1)
    assert out["deleted_count"] == 0
    remaining = sorted(
        p.name for p in root.iterdir() if p.is_dir() and p.name.isdigit()
    )
    assert remaining == ["1", "2", "3", "4", "5"]


def test_prune_scan_root_keeps_newest_dates(tmp_path: Path) -> None:
    root = tmp_path / "scan"
    for day in ("20240108", "20240109", "20240110", "20240111"):
        (root / day).mkdir(parents=True)
    (root / "notes").mkdir()
    deleted = ArtifactStore.prune_scan_root(root, max_versions=2)
    assert deleted == 2
    remaining = sorted(p.name for p in root.iterdir() if p.is_dir())
    assert remaining == ["20240110", "20240111", "notes"]


def test_allocate_reuses_version_id_for_step(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "simulations"
    monkeypatch.setattr(
        EnumerateStore,
        "simulations_root",
        classmethod(lambda cls, folder: root),
    )
    monkeypatch.setattr(
        PriceFactorStore,
        "simulations_root",
        classmethod(lambda cls, folder: root),
    )
    enum_store = EnumerateStore.allocate(tmp_path, strategy_id="demo")
    price_store = PriceFactorStore.allocate(
        tmp_path,
        strategy_id="demo",
        version_id=enum_store.version_id,
    )
    assert enum_store.version_id == price_store.version_id == "1"
    assert enum_store.output_dir == root / "1" / "enum"
    assert price_store.output_dir == root / "1" / "price"
    meta = json.loads((root / "meta.json").read_text(encoding="utf-8"))
    assert meta["next_version_id"] == 2


def test_allocate_does_not_cap_live_versions(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "simulations"
    monkeypatch.setattr(
        PortfolioStore,
        "simulations_root",
        classmethod(lambda cls, folder: root),
    )
    ids = []
    for _ in range(4):
        store = PortfolioStore.allocate(tmp_path, strategy_id="demo/s")
        ids.append(int(store.version_id))
    assert ids == [1, 2, 3, 4]
    remaining = sorted(
        int(p.name) for p in root.iterdir() if p.is_dir() and p.name.isdigit()
    )
    assert remaining == [1, 2, 3, 4]
    assert (root / "4" / "portfolio").is_dir()


def test_latest_reads_meta(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "simulations"
    (root / "2" / "price").mkdir(parents=True)
    (root / "meta.json").write_text(
        '{"next_version_id": 3}', encoding="utf-8"
    )
    monkeypatch.setattr(
        PriceFactorStore,
        "simulations_root",
        classmethod(lambda cls, folder: root),
    )
    store = PriceFactorStore.latest(tmp_path)
    assert store is not None
    assert isinstance(store, PriceFactorStore)
    assert store.version_id == "2"
    assert store.output_dir == root / "2" / "price"


def test_write_json_at_roundtrip(tmp_path: Path) -> None:
    ArtifactStore.write_json_at(tmp_path, "overall_report", {"ok": True})
    assert ArtifactStore.read_json_at(tmp_path, "overall_report") == {"ok": True}


def test_scan_at_uses_date_dir(tmp_path: Path, monkeypatch) -> None:
    scan_root = tmp_path / "scan"
    monkeypatch.setattr(
        ArtifactStore,
        "scan_root",
        classmethod(lambda cls, folder: scan_root),
    )
    store = ArtifactStore.scan_at(tmp_path, "20240110")
    assert store.output_dir == scan_root / "20240110"
    store.write_summary({"date": "20240110", "total_opportunities": 0})
    assert store.has_summary()
    assert store.read_summary()["total_opportunities"] == 0


def test_scan_store_does_not_import_engines() -> None:
    import core.modules.strategy.core.services.artifacts.scan_store as mod

    text = Path(mod.__file__).read_text(encoding="utf-8")
    assert "engines" not in text

