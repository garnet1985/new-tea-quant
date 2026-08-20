"""枚举 signal_snapshot sidecar CSV：按实体扁表、空 capture 不落盘。"""
from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import pytest

from core.modules.strategy.core.engines.enumerator.common.report_manager.stock_investments import (
    InvestmentsReport,
)
from core.modules.strategy.core.services.artifacts import (
    SIGNAL_SNAPSHOTS_SUFFIX,
    STOCK_INVESTMENTS_SUFFIX,
    ArtifactStore,
    EntitySignalSnapshotCsv,
    EnumerateStore,
)

pytestmark = pytest.mark.force_run


@pytest.fixture(autouse=True)
def _clear_store_cache():
    ArtifactStore.clear_cache()
    yield
    ArtifactStore.clear_cache()


def _store(output_dir: Path) -> EnumerateStore:
    return EnumerateStore.at(output_dir)


def _payload(investment_id: str, snapshot: dict | None = None) -> dict:
    return {
        "meta": {"opportunity_id": investment_id},
        "trigger_date": "20240102",
        "trigger_price": 10.0,
        "lifecycle": "complete",
        "entry": {},
        "exit_info": {},
        "holding": {},
        "outcome": {},
        "signal_snapshot": dict(snapshot or {}),
    }


def test_build_skips_empty_snapshots() -> None:
    csv = EntitySignalSnapshotCsv.build(
        "688005.SH",
        [
            _payload("1", {"rsi": 18.2}),
            _payload("2", {}),
            _payload("3"),
        ],
    )
    assert [row.investment_id for row in csv.rows] == ["1"]
    assert csv.rows[0].values["rsi"] == 18.2


def test_save_omits_file_when_no_captures(tmp_path: Path) -> None:
    csv = EntitySignalSnapshotCsv.build("688005.SH", [_payload("1", {})])
    _store(tmp_path).write_snapshots(csv)
    path = tmp_path / "entities" / f"688005.SH{SIGNAL_SNAPSHOTS_SUFFIX}"
    assert not path.exists()


def test_save_unions_keys_and_roundtrips(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.write_snapshots(
        EntitySignalSnapshotCsv.build(
            "688005.SH",
            [
                _payload("1", {"rsi": 18.2, "pe_percentile": 22.1}),
                _payload("2", {"rsi": 19.1}),
            ],
        )
    )

    ArtifactStore.clear_cache()
    loaded = _store(tmp_path).snapshots("688005.SH")
    assert [row.investment_id for row in loaded.rows] == ["1", "2"]
    header = loaded.rows[0].values.keys()
    assert list(header) == ["pe_percentile", "rsi"]
    assert loaded.rows[0].values["rsi"] == "18.2"
    assert loaded.rows[0].values["pe_percentile"] == "22.1"
    assert loaded.rows[1].values["rsi"] == "19.1"
    assert loaded.rows[1].values["pe_percentile"] == ""


def test_append_unions_new_keys(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.write_snapshots(
        EntitySignalSnapshotCsv.build(
            "688005.SH",
            [_payload("1", {"rsi": 18.2})],
        )
    )
    store.write_snapshots(
        EntitySignalSnapshotCsv.build(
            "688005.SH",
            [_payload("2", {"pe_percentile": 15.0})],
        ),
        append=True,
    )

    ArtifactStore.clear_cache()
    loaded = _store(tmp_path).snapshots("688005.SH")
    assert [row.investment_id for row in loaded.rows] == ["1", "2"]
    assert loaded.rows[0].values["rsi"] == "18.2"
    assert loaded.rows[0].values["pe_percentile"] == ""
    assert loaded.rows[1].values["rsi"] == ""
    assert loaded.rows[1].values["pe_percentile"] == "15.0"


def test_report_writes_sidecar_not_trading_columns(tmp_path: Path) -> None:
    report = InvestmentsReport(SimpleNamespace(output_dir=tmp_path, version_id="1"))
    report.append_entity(
        "688005.SH",
        [
            _payload("1", {"rsi": 18.2, "hit": True}),
            _payload("2", {}),
        ],
    )

    entities = tmp_path / "entities"
    sidecar = entities / f"688005.SH{SIGNAL_SNAPSHOTS_SUFFIX}"
    trading = entities / f"688005.SH{STOCK_INVESTMENTS_SUFFIX}"
    assert sidecar.is_file()
    assert trading.is_file()

    snapshots = _store(tmp_path).snapshots("688005.SH")
    assert [row.investment_id for row in snapshots.rows] == ["1"]
    assert snapshots.rows[0].values["rsi"] == "18.2"
    assert snapshots.rows[0].values["hit"] == "1"

    investments = _store(tmp_path).investments("688005.SH")
    assert [row.investment_id for row in investments.rows] == ["1", "2"]
    trading_header = trading.read_text(encoding="utf-8").splitlines()[0]
    assert "signal_snapshot" not in trading_header
    assert "rsi" not in trading_header.split(",")


def test_report_omits_sidecar_when_all_empty(tmp_path: Path) -> None:
    report = InvestmentsReport(SimpleNamespace(output_dir=tmp_path, version_id="1"))
    report.append_entity("688005.SH", [_payload("1", {})])
    sidecar = tmp_path / "entities" / f"688005.SH{SIGNAL_SNAPSHOTS_SUFFIX}"
    trading = tmp_path / "entities" / f"688005.SH{STOCK_INVESTMENTS_SUFFIX}"
    assert not sidecar.exists()
    assert trading.is_file()
