"""ScanDateResolver 单元测试。"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from core.modules.strategy.core.engines.scanner.helpers.date_resolver import (
    ScanDateResolver,
)

pytestmark = pytest.mark.force_run


class _FakeCalendar:
    def __init__(self, *, strict: str = "", freshness: str = "") -> None:
        self._strict = strict
        self._freshness = freshness

    def get_real_world_latest_completed_trading_date(self) -> str:
        return self._strict


class _FakeKline:
    def __init__(self, latest: str) -> None:
        self._latest = latest

    def load_latest_date(self, term: str) -> str:
        _ = term
        return self._latest


class _FakeTable:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = rows

    def load_by_date(self, date: str) -> List[Dict[str, Any]]:
        _ = date
        return list(self._rows)


def _dm(*, latest: str, rows: List[Dict[str, Any]], strict: str = "20240110") -> Any:
    return SimpleNamespace(
        stock=SimpleNamespace(kline=_FakeKline(latest)),
        service=SimpleNamespace(calendar=_FakeCalendar(strict=strict)),
        get_table=lambda name: _FakeTable(rows) if name == "sys_stock_klines" else None,
    )


def test_resolve_strict_scan_date(monkeypatch: pytest.MonkeyPatch) -> None:
    dm = _dm(
        latest="20240110",
        strict="20240110",
        rows=[{"id": "600000.SH"}, {"id": "000001.SZ"}],
    )
    resolver = ScanDateResolver(dm)
    day, ids, meta = resolver.resolve_scan_date_with_meta(use_strict=True)
    assert day == "20240110"
    assert ids == ["000001.SZ", "600000.SH"]
    assert meta["mode"] == "strict"
    assert meta["use_strict"] is True
    assert "真实世界" in meta["source_detail"]


def test_anchor_clamps_to_kline_latest(monkeypatch: pytest.MonkeyPatch) -> None:
    dm = _dm(latest="20240105", strict="20240110", rows=[{"id": "600000.SH"}])

    def _fake_freshness(_dm: Any) -> str:
        return "20240110"

    monkeypatch.setattr(
        "core.modules.data_source.core.catalog.freshness_probe._resolve_freshness_end_date",
        _fake_freshness,
    )
    meta = ScanDateResolver.resolve_anchor_meta(dm, use_strict=False)
    assert meta["scan_date"] == "20240105"
    assert meta["clamped_to_kline"] is True
    assert meta["mode"] == "non_strict"


def test_resolve_raises_when_no_stocks() -> None:
    dm = _dm(latest="20240110", strict="20240110", rows=[])
    resolver = ScanDateResolver(dm)
    with pytest.raises(ValueError, match="no kline"):
        resolver.resolve_scan_date(use_strict=True)


def test_non_strict_meta_mentions_data_json(monkeypatch: pytest.MonkeyPatch) -> None:
    dm = _dm(latest="20240110", strict="20240110", rows=[{"id": "600000.SH"}])

    def _fake_freshness(_dm: Any) -> str:
        return "20240110"

    monkeypatch.setattr(
        "core.modules.data_source.core.catalog.freshness_probe._resolve_freshness_end_date",
        _fake_freshness,
    )
    monkeypatch.setattr(
        "core.infra.project_context.ProjectContext.config.get_as_of_latest_completed_trading_date",
        lambda: "20240115",
    )
    meta = ScanDateResolver.resolve_anchor_meta(dm, use_strict=False)
    assert meta["mode"] == "non_strict"
    assert meta["source"] == "data_json_as_of"
    assert "data.json" in meta["source_detail"]
    assert meta["configured_as_of"] == "20240115"
