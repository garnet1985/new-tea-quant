"""Tests for BFF stock detail (V2-07c)."""

from __future__ import annotations

from unittest.mock import patch

from core.bff.APIs.strategy.routes.report.stock_detail import WorkbenchStockDetail
from core.modules.strategy.core.engines.shared.enum_result_contract import EnumResult
from core.modules.strategy.core.services.artifacts import (
    GoalAchievementRow,
    PriceInvestmentRow,
)


def test_enum_markers_use_trigger_date():
    inv = EnumResult(
        investment_id="opp1",
        trigger_date="20200102",
        trigger_price=10.5,
        entry_date="20200103",
        exit_date="20200110",
        lifecycle="complete",
        result="win",
        exit_reason="take_profit",
    )
    candles = [
        {"date": "20200102", "open": 10, "high": 11, "low": 9, "close": 10.2},
    ]
    markers = WorkbenchStockDetail._enum_markers([inv], candles)
    assert len(markers) == 1
    assert markers[0]["type"] == "opportunity"
    assert markers[0]["detail"]["entry_date"] == "20200103"
    assert markers[0]["detail"]["result"] == "win"


def test_price_markers_enter_and_exit():
    inv = PriceInvestmentRow(
        opportunity_id="p1",
        enter_date="20200102",
        enter_price=10.0,
        exit_date="20200105",
        exit_price=11.0,
        roi=0.1,
        lifecycle="complete",
        result="win",
        exit_reason="take_profit",
    )
    candles = [
        {"date": "20200102", "open": 10, "high": 11, "low": 9, "close": 10},
        {"date": "20200105", "open": 11, "high": 12, "low": 10, "close": 11},
    ]
    markers = WorkbenchStockDetail._price_markers([inv], candles)
    types = [m["type"] for m in markers]
    assert types == ["buy", "target_win"]
    assert markers[0]["detail"]["entry_date"] == "20200102"
    assert markers[1]["detail"]["exit_date"] == "20200105"


def test_price_markers_emit_each_completed_goal():
    inv = PriceInvestmentRow(
        opportunity_id="p1",
        enter_date="20200102",
        enter_price=10.0,
        exit_date="20200105",
        exit_price=11.0,
        roi=0.075,
        lifecycle="complete",
        result="win",
        exit_reason="take_profit",
    )
    candles = [
        {"date": "20200102", "open": 10, "high": 11, "low": 9, "close": 10},
        {"date": "20200104", "open": 10.4, "high": 10.8, "low": 10.2, "close": 10.5},
        {"date": "20200105", "open": 11, "high": 12, "low": 10, "close": 11},
    ]
    goals = [
        GoalAchievementRow(
            investment_id="p1",
            goal_name="win20%",
            date="20200104",
            price=10.5,
            exit_ratio=0.5,
            reason="take_profit",
            roi=0.05,
        ),
        GoalAchievementRow(
            investment_id="p1",
            goal_name="win30%",
            date="20200105",
            price=11.0,
            exit_ratio=0.5,
            reason="take_profit",
            roi=0.1,
        ),
    ]
    markers = WorkbenchStockDetail._price_markers([inv], candles, goal_rows=goals)
    types = [m["type"] for m in markers]
    dates = [m["date"] for m in markers]
    assert types == ["buy", "target_win", "target_win"]
    assert dates == ["20200102", "20200104", "20200105"]
    assert markers[1]["detail"]["goal_name"] == "win20%"
    assert markers[1]["detail"]["exit_ratio"] == 0.5
    assert markers[2]["detail"]["goal_name"] == "win30%"


def test_enum_metrics_for_stock():
    rows = [
        EnumResult(lifecycle="complete", result="win", weighted_roi=0.1),
        EnumResult(lifecycle="complete", result="loss", weighted_roi=-0.1),
        EnumResult(lifecycle="open", result="", weighted_roi=0.0),
    ]
    metrics = WorkbenchStockDetail._enum_metrics_for_stock(rows)
    assert metrics["totalOpportunities"] == 3
    assert metrics["completedCount"] == 2
    assert metrics["winCount"] == 1
    assert metrics["lossCount"] == 1


@patch.object(WorkbenchStockDetail, "_build_enum")
@patch(
    "core.bff.APIs.strategy.routes.report.stock_detail.WorkbenchSnapshots.fetch_by_version"
)
def test_build_routes_enum(mock_fetch, mock_enum):
    mock_fetch.return_value = {"version": 3, "result_report": {}}
    mock_enum.return_value = {"step": "enum", "detail_available": True}
    msg = WorkbenchStockDetail.build(
        strategy_name="demo/x",
        normalized_step="enum",
        version=3,
        stock_id="000001.SZ",
    )
    assert msg["detail_available"] is True
    mock_enum.assert_called_once()


@patch(
    "core.bff.APIs.strategy.routes.report.stock_detail.WorkbenchSnapshots.fetch_by_version",
    return_value=None,
)
def test_build_missing_snapshot(_mock_fetch):
    assert (
        WorkbenchStockDetail.build(
            strategy_name="demo/x",
            normalized_step="enum",
            version=1,
            stock_id="000001.SZ",
        )
        is None
    )


def test_resolve_output_dir_accepts_enum_json(tmp_path, monkeypatch):
    out_dir = tmp_path / "9"
    entities = out_dir / "entities"
    entities.mkdir(parents=True)
    (entities / "000001.SZ.json").write_text(
        '{"kind":"enum_results","entity_id":"000001.SZ","results":[]}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.bff.APIs.strategy.routes.report.stock_detail.Strategy.resolve_simulation_output_dirs",
        lambda *a, **k: [out_dir],
    )
    resolved = WorkbenchStockDetail._resolve_output_dir(
        "demo/x", "enum", {"output_dir": str(out_dir)}, 9, entity_id="000001.SZ"
    )
    assert resolved == out_dir
