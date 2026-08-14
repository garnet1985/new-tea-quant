"""Tests for BFF step report builders (V2-07 / V2-07b)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from core.bff.APIs.strategy.routes.report.step_report import WorkbenchReports


@patch.object(WorkbenchReports, "_resolve_step_report")
@patch(
    "core.bff.APIs.strategy.routes.report.step_report.WorkbenchSnapshots.fetch_by_version"
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
    "core.bff.APIs.strategy.routes.report.step_report.WorkbenchSnapshots.fetch_by_version"
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
        "core.bff.APIs.strategy.routes.report.step_report.resolve_simulation_output_dirs",
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


@patch.object(WorkbenchReports, "_enrich_stock_ref_with_list_names", side_effect=lambda x: x)
@patch(
    "core.bff.APIs.strategy.routes.report.step_report.WorkbenchSnapshots.fetch_by_version"
)
def test_build_step_report_ref_empty_entity_list_is_available(
    mock_fetch, _mock_enrich, tmp_path, monkeypatch
):
    """0 机会时 entity_list.rows=[] → stock_ref={} 仍应 available（勿当成需重跑）。"""
    out_dir = tmp_path / "3"
    out_dir.mkdir(parents=True)
    (out_dir / "entity_list.json").write_text(
        json.dumps(
            {
                "strategy_key": "demo",
                "version_id": 3,
                "rows": [],
                "created_at": "",
            }
        ),
        encoding="utf-8",
    )
    mock_fetch.return_value = {
        "version": 3,
        "result_report": {"enum": {"output_dir": str(out_dir)}},
    }
    monkeypatch.setattr(
        "core.bff.APIs.strategy.routes.report.step_report.resolve_simulation_output_dirs",
        lambda *a, **k: [out_dir],
    )

    msg = WorkbenchReports.build_step_report_ref(
        strategy_name="demo/x",
        normalized_step="enum",
        version=3,
    )
    assert msg["stock_ref_available"] is True
    assert msg["stock_ref"] == {}
