"""Tests for workbench report adapters (V2-07 / V2-07b)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from core.modules.strategy.core.bff_support.report_hydrate import (
    hydrate_enum_slot,
    hydrate_portfolio_slot,
    hydrate_price_slot,
)
from core.modules.strategy.core.bff_support.workbench_reports import WorkbenchReports


def _write_overall(path: Path, summary: dict, **extra) -> None:
    body = {
        "strategy_key": "demo",
        "strategy_path": "demo/x",
        "version_id": 1,
        "execution_mode": "entity_based",
        "backtest_period": {"start_date": "2020-01-01", "end_date": "2020-12-31"},
        "summary": summary,
        "created_at": "2020-01-01T00:00:00",
        **extra,
    }
    path.write_text(json.dumps(body), encoding="utf-8")


def test_hydrate_enum_slot_from_overall_report(tmp_path, monkeypatch):
    out_dir = tmp_path / "1"
    out_dir.mkdir()
    _write_overall(
        out_dir / "overall_report.json",
        {
            "total_opportunities": 12,
            "total_stocks": 10,
            "trigger_stocks": 4,
            "trigger_ratio": 0.4,
            "avg_per_stock": 1.2,
            "completed_ratio": 0.5,
            "completed_count": 2,
            "unfinished_count": 2,
        },
    )

    monkeypatch.setattr(
        "core.modules.strategy.core.bff_support.report_hydrate.resolve_simulation_output_dirs",
        lambda *a, **k: [out_dir],
    )

    slot = hydrate_enum_slot("demo/x", {"output_dir": str(out_dir), "success": True})
    assert slot["enumMetrics"]["totalOpportunities"] == 12
    assert slot["success"] is True


def test_hydrate_price_slot_from_overall_report(tmp_path, monkeypatch):
    out_dir = tmp_path / "2"
    out_dir.mkdir()
    _write_overall(
        out_dir / "overall_report.json",
        {
            "win_rate": 0.5,
            "avg_roi": 0.1,
            "avg_duration_in_days": 5.0,
            "annual_return": 0.2,
            "total_investments": 3,
            "stocks_have_opportunities": 2,
        },
        enum_version_id="1",
    )

    monkeypatch.setattr(
        "core.modules.strategy.core.bff_support.report_hydrate.resolve_simulation_output_dirs",
        lambda *a, **k: [out_dir],
    )
    slot = hydrate_price_slot("demo/x", {"output_dir": str(out_dir)})
    assert slot["priceMetrics"]["totalInvestments"] == 3


def test_hydrate_portfolio_slot_from_overall_report(tmp_path, monkeypatch):
    out_dir = tmp_path / "3"
    out_dir.mkdir()
    _write_overall(
        out_dir / "overall_report.json",
        {
            "initial_capital": 100000.0,
            "final_total_equity": 110000.0,
            "total_return": 0.1,
            "win_rate": 0.5,
            "total_trades": 4,
        },
        enum_version_id="1",
    )

    monkeypatch.setattr(
        "core.modules.strategy.core.bff_support.report_hydrate.resolve_simulation_output_dirs",
        lambda *a, **k: [out_dir],
    )
    slot = hydrate_portfolio_slot("demo/x", {"output_dir": str(out_dir)})
    assert slot["capitalMetrics"]["initialCapital"] == 100000.0


@patch.object(WorkbenchReports, "_resolve_step_report")
@patch(
    "core.modules.strategy.core.bff_support.workbench_reports.WorkbenchSnapshots.fetch_by_version"
)
def test_build_step_report_message(mock_fetch, mock_resolve):
    mock_fetch.return_value = {"version": 5, "result_report": {"enum": {"success": True}}}
    mock_resolve.return_value = {"enumMetrics": {"totalOpportunities": 9}}

    msg = WorkbenchReports.build_step_report(
        strategy_name="demo/x",
        normalized_step="enum",
        version=5,
    )
    assert msg["version_id"] == "v5"
    assert msg["step"] == "enum"
    assert msg["report"]["enumMetrics"]["totalOpportunities"] == 9


@patch.object(WorkbenchReports, "_enrich_stock_ref_with_list_names", side_effect=lambda x: x)
@patch(
    "core.modules.strategy.core.bff_support.workbench_reports.WorkbenchSnapshots.fetch_by_version"
)
def test_build_step_report_ref_from_entity_list(mock_fetch, _mock_enrich, tmp_path, monkeypatch):
    out_dir = tmp_path / "7"
    entities = out_dir / "entities"
    entities.mkdir(parents=True)
    (entities / "000001.SZ_stock_investments.csv").write_text(
        "a,b\n1,2\n", encoding="utf-8"
    )
    entity_list = {
        "strategy_key": "demo",
        "version_id": 7,
        "rows": [
            {
                "entity_id": "000001.SZ",
                "stock_name": "平安",
                "opportunities": 3,
                "completion_rate": 0.5,
                "avg_gap_days": 12.0,
            }
        ],
        "created_at": "",
    }
    (out_dir / "entity_list.json").write_text(
        json.dumps(entity_list), encoding="utf-8"
    )

    mock_fetch.return_value = {
        "version": 7,
        "result_report": {"enum": {"output_dir": str(out_dir)}},
    }
    monkeypatch.setattr(
        "core.modules.strategy.core.bff_support.workbench_reports.resolve_simulation_output_dirs",
        lambda *a, **k: [out_dir],
    )

    msg = WorkbenchReports.build_step_report_ref(
        strategy_name="demo/x",
        normalized_step="enum",
        version=7,
    )
    assert msg["stock_ref_available"] is True
    ref = msg["stock_ref"]["000001.SZ"]
    assert ref["opportunities"] == 3
    assert ref["avg_gap_days"] == 12.0


@patch(
    "core.modules.strategy.core.bff_support.workbench_reports.WorkbenchSnapshots.fetch_by_version",
    return_value=None,
)
def test_build_step_report_missing_row(_mock_fetch):
    assert (
        WorkbenchReports.build_step_report(
            strategy_name="demo/x", normalized_step="enum", version=1
        )
        is None
    )
