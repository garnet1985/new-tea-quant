"""Tests for workbench report_hydrate (still used by snapshots + BFF report)."""

from __future__ import annotations

import json
from pathlib import Path

from core.modules.strategy.launcher.report_hydrate import (
    hydrate_enum_slot,
    hydrate_portfolio_slot,
    hydrate_price_slot,
)


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
        "core.modules.strategy.launcher.report_hydrate.resolve_simulation_output_dirs",
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
        "core.modules.strategy.launcher.report_hydrate.resolve_simulation_output_dirs",
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
        "core.modules.strategy.launcher.report_hydrate.resolve_simulation_output_dirs",
        lambda *a, **k: [out_dir],
    )
    slot = hydrate_portfolio_slot("demo/x", {"output_dir": str(out_dir)})
    assert slot["capitalMetrics"]["initialCapital"] == 100000.0
