"""ScanStore / scanner ReportManager 落盘测试。"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.strategy.core.engines.scanner.report_manager import ReportManager
from core.modules.strategy.core.engines.shared.data_class.opportunity import (
    Opportunity,
    StockInfo,
)
from core.modules.strategy.core.services.artifacts import ArtifactStore, ScanStore

pytestmark = pytest.mark.force_run


def _isolate_scan_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    scan_dir = tmp_path / "scan"
    monkeypatch.setattr(
        ArtifactStore,
        "scan_root",
        classmethod(lambda cls, folder: scan_dir),
    )
    return scan_dir


def test_scan_store_save_load_and_prune(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _isolate_scan_dir(tmp_path, monkeypatch)
    store = ArtifactStore.scan_at("demo_strategy", "20240110")
    assert isinstance(store, ScanStore)
    opp = Opportunity(
        stock=StockInfo(id="600000.SH", name="浦发"),
        record_of_today={"date": "20240110", "close": 10.0},
        trigger_date="20240110",
        trigger_price=10.0,
    )
    store.write_opportunity_rows([opp.to_dict()])
    loaded = ReportManager.load_opportunities(store)
    assert len(loaded) == 1
    assert loaded[0].stock_id == "600000.SH"
    assert loaded[0].trigger_price == pytest.approx(10.0)

    empty = ArtifactStore.scan_at("demo_strategy", "20240111")
    empty.write_opportunity_rows([])
    assert not empty.file("opportunities").is_file()

    scan_root = ArtifactStore.scan_root("demo_strategy")
    for day in ("20240108", "20240109", "20240110"):
        (scan_root / day).mkdir(parents=True, exist_ok=True)
        (scan_root / day / "opportunities.csv").write_text("x\n", encoding="utf-8")
    ArtifactStore.prune_scan_root(scan_root, max_versions=2)
    remaining = sorted(d.name for d in scan_root.iterdir() if d.is_dir())
    assert remaining == ["20240109", "20240110"]


def test_report_manager_writes_scan_summary_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_dir = _isolate_scan_dir(tmp_path, monkeypatch)
    mgr = ReportManager.begin(
        strategy_key="demo",
        scan_date="20240110",
        stock_ids=["600000.SH", "000001.SZ"],
        adapter_names=[],
    )
    mgr.collect(
        Opportunity(
            stock=StockInfo(id="600000.SH", name="浦发"),
            record_of_today={"date": "20240110", "close": 10.0},
            trigger_date="20240110",
            trigger_price=10.0,
        )
    )
    report = mgr.finalize(present=False)
    summary_path = scan_dir / "20240110" / "scan_summary.json"
    csv_path = scan_dir / "20240110" / "opportunities.csv"
    assert summary_path.is_file()
    assert csv_path.is_file()
    assert report["total_opportunities"] == 1
    assert report["total_stocks"] == 2
    assert report["summary"]["total_stocks"] == 1


def test_report_manager_writes_empty_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scan_dir = _isolate_scan_dir(tmp_path, monkeypatch)
    mgr = ReportManager.begin(
        strategy_key="demo",
        scan_date="20240110",
        stock_ids=["600000.SH"],
        adapter_names=[],
    )
    report = mgr.finalize(present=False)
    summary_path = scan_dir / "20240110" / "scan_summary.json"
    csv_path = scan_dir / "20240110" / "opportunities.csv"
    assert summary_path.is_file()
    assert not csv_path.is_file()
    assert report["total_opportunities"] == 0
