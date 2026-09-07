"""Portfolio event timeline DTO (full equity curve + trades)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.bff.APIs.strategy.helpers.portfolio_event_timeline import (
    attach_portfolio_event_timeline,
    build_portfolio_event_timeline,
)
from core.bff.APIs.strategy.helpers.report_hydrate import hydrate_portfolio_slot


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_build_timeline_from_curve_and_trades(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "core.bff.APIs.strategy.helpers.portfolio_event_timeline._enrich_stock_names",
        lambda events: None,
    )
    out_dir = tmp_path / "3"
    out_dir.mkdir()
    _write_json(
        out_dir / "equity_curve.json",
        [
            {"date": "20240103", "cash": 900000.0, "equity": 1000000.0, "open_positions": 1},
            {"date": "20240110", "cash": 800000.0, "equity": 980000.0, "open_positions": 2},
            {"date": "20240117", "cash": 1100000.0, "equity": 1100000.0, "open_positions": 0},
        ],
    )
    _write_json(
        out_dir / "trades.json",
        [
            {
                "date": "2024-01-03",
                "entity_id": "000001.SZ",
                "investment_id": "1",
                "side": "buy",
                "shares": 100,
                "price": 10.5,
                "amount": 1050.0,
                "fees": 1.0,
                "total_cost": 1051.0,
            },
            {
                "date": "20240117",
                "entity_id": "000001.SZ",
                "investment_id": "1",
                "side": "sell",
                "shares": 100,
                "price": 12.0,
                "profit": 150.0,
            },
        ],
    )

    timeline = build_portfolio_event_timeline(out_dir, initial_capital=1000000.0)
    assert timeline is not None
    assert timeline["eventCurveLabels"] == ["20240103", "20240110", "20240117"]
    assert timeline["eventCurveValues"] == [1000000.0, 980000.0, 1100000.0]
    assert timeline["eventDrawdownValues"][1] > 0
    assert timeline["eventDrawdownValues"][2] == 0
    sides = {row["side"] for row in timeline["tradeEvents"]}
    assert sides == {"buy", "sell"}
    assert timeline["tradeEvents"][0]["date"] == "20240103"
    assert timeline["tradeEvents"][0]["entityId"] == "000001.SZ"
    assert timeline["tradeEvents"][0]["shares"] == 100
    assert timeline["tradeEvents"][0]["price"] == 10.5
    assert timeline["tradeEvents"][0]["cost"] == 1051.0
    assert timeline["tradeEvents"][1]["profit"] == 150.0
    assert timeline["tradeEvents"][1]["buyPrice"] == 10.5


def test_build_timeline_clamps_negative_sell_price(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "core.bff.APIs.strategy.helpers.portfolio_event_timeline._enrich_stock_names",
        lambda events: None,
    )
    out_dir = tmp_path / "4"
    out_dir.mkdir()
    _write_json(
        out_dir / "equity_curve.json",
        [
            {"date": "20240103", "cash": 1, "equity": 100.0, "open_positions": 1},
            {"date": "20240131", "cash": 1, "equity": 90.0, "open_positions": 0},
        ],
    )
    _write_json(
        out_dir / "trades.json",
        [
            {
                "date": "20240131",
                "entity_id": "920522.BJ",
                "side": "sell",
                "shares": 200,
                "price": -8.72,
                "profit": -6419.0,
            }
        ],
    )
    timeline = build_portfolio_event_timeline(out_dir, initial_capital=100.0)
    assert timeline["tradeEvents"][0]["price"] == 0.0
    # -8.72 且亏损 6419 → 反推入价约 23.375；归零后盈利 = 200 × (0 - 入价)
    assert timeline["tradeEvents"][0]["buyPrice"] == pytest.approx(23.375)
    assert timeline["tradeEvents"][0]["profit"] == pytest.approx(-4675.0)


def test_build_timeline_missing_curve_returns_none(tmp_path: Path):
    out_dir = tmp_path / "9"
    out_dir.mkdir()
    assert build_portfolio_event_timeline(out_dir) is None


def test_attach_skips_when_already_present(tmp_path: Path):
    slot = {
        "capitalMetrics": {
            "initialCapital": 1,
            "eventCurveLabels": ["20240101", "20240102"],
            "tradeEvents": [],
        }
    }
    out = attach_portfolio_event_timeline(slot, [tmp_path])
    assert out["capitalMetrics"]["eventCurveLabels"] == ["20240101", "20240102"]


def test_hydrate_attaches_timeline_when_metrics_already_present(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "core.bff.APIs.strategy.helpers.portfolio_event_timeline._enrich_stock_names",
        lambda events: None,
    )
    out_dir = tmp_path / "3"
    out_dir.mkdir()
    _write_json(
        out_dir / "equity_curve.json",
        [
            {"date": "20240103", "cash": 1, "equity": 100.0, "open_positions": 0},
            {"date": "20240104", "cash": 1, "equity": 110.0, "open_positions": 0},
        ],
    )
    _write_json(
        out_dir / "trades.json",
        [
            {
                "date": "20240103",
                "entity_id": "688005.SH",
                "side": "buy",
                "shares": 200,
                "price": 8.0,
            }
        ],
    )
    monkeypatch.setattr(
        "core.bff.APIs.strategy.helpers.report_hydrate.Strategy.resolve_simulation_output_dirs",
        lambda *a, **k: [out_dir],
    )
    slot = hydrate_portfolio_slot(
        "demo/x",
        {"output_dir": str(out_dir), "capitalMetrics": {"initialCapital": 100000.0, "totalTrades": 1}},
    )
    assert slot["capitalMetrics"]["initialCapital"] == 100000.0
    assert slot["capitalMetrics"]["eventCurveLabels"] == ["20240103", "20240104"]
    assert slot["capitalMetrics"]["tradeEvents"][0]["entityId"] == "688005.SH"
    assert slot["capitalMetrics"]["tradeEvents"][0]["shares"] == 200
