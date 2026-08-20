"""price_factor ReportManager：三报告稿落盘。"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.modules.strategy.core.engines.price_factor.report_manager import ReportManager
from core.modules.strategy.core.services.artifacts import (
    ENTITY_LIST_FILE,
    OVERALL_REPORT_FILE,
    PERFORMANCE_FILE,
    EnumerateStore,
    PriceFactorStore,
    PriceInvestmentRow,
)

pytestmark = pytest.mark.force_run


def _write_enum_runtime(output_dir: Path, entity_ids: list[str]) -> None:
    store = EnumerateStore.at(output_dir)
    store.write_text_lines("entity_ids", entity_ids)
    store.write_json(
        "runtime_env",
        {
            "strategy_key": "rsi_v1",
            "strategy_path": "demo/regression/rsi/rsi_v1_without_value_anchor",
            "version_id": 1,
            "execution_mode": "entity_based",
            "market_profile": "china_a_stock",
            "period": {"start_date": "20240102", "end_date": "20240110"},
            "settings_fp": "s",
            "env_fp": "e",
            "system": {},
            "settings_snapshot": {"effective_settings": {}, "settings_diff": {}},
        },
    )


def test_report_manager_finalize_writes_globals(tmp_path: Path, monkeypatch) -> None:
    enum_dir = tmp_path / "enum" / "1"
    _write_enum_runtime(enum_dir, ["000001.SZ"])
    data = EnumerateStore.open(enum_dir, version_id="1")

    price_root = tmp_path / "price"
    monkeypatch.setattr(
        PriceFactorStore,
        "simulation_root",
        classmethod(lambda cls, folder, kind=None: price_root),
    )

    ctx = SimpleNamespace(
        strategy_info=SimpleNamespace(
            key="rsi_v1",
            unique_relative_path="demo/regression/rsi/rsi_v1_without_value_anchor",
        ),
        strategy_key="demo/regression/rsi/rsi_v1_without_value_anchor",
        strategy_folder=tmp_path,
        settings_fp="sfp",
        env_fp="efp",
    )
    report = ReportManager.begin(ctx, data, start="20240102", end="20240110")
    PriceFactorStore.at(report.output_dir).write_investments(
        "000001.SZ",
        [
            PriceInvestmentRow(
                opportunity_id="opp_1",
                enter_date="20240103",
                enter_price=10.0,
                exit_date="20240105",
                exit_price=11.0,
                roi=0.1,
                holding_days=2,
                result="win",
                lifecycle="complete",
                exit_reason="take_profit",
            )
        ],
    )
    result = report.finalize(
        SimpleNamespace(
            success=True,
            total_jobs=1,
            completed_jobs=1,
            failed_jobs=0,
            elapsed_seconds=1.2,
        ),
        data=data,
    )

    assert result["success"] is True
    assert result["priceMetrics"]["totalInvestments"] == 1
    assert result["priceMetrics"]["totalWinInvestments"] == 1
    assert result["summary"]["total_investments"] == 1
    assert result["summary"]["total_win_investments"] == 1
    store = PriceFactorStore.at(report.output_dir)
    assert store.file("runtime_env").is_file()
    assert store.file("overall_report").is_file()
    assert store.file("entity_list").is_file()
    assert store.file("performance").is_file()
    assert store.file("entity_ids").is_file()
    assert store.has_investments("000001.SZ")

    overall = json.loads(
        (report.output_dir / OVERALL_REPORT_FILE).read_text(encoding="utf-8")
    )
    assert "entity_summaries" not in overall
    assert "win_rate" in overall["summary"]
    assert "avg_duration_in_days" in overall["summary"]

    entity_list = json.loads(
        (report.output_dir / ENTITY_LIST_FILE).read_text(encoding="utf-8")
    )
    assert len(entity_list["rows"]) == 1
    assert entity_list["rows"][0]["entity_id"] == "000001.SZ"
    assert entity_list["rows"][0]["total_investments"] == 1

    perf = json.loads(
        (report.output_dir / PERFORMANCE_FILE).read_text(encoding="utf-8")
    )
    assert perf["elapsed_seconds"] == 1.2
    assert perf["completed_jobs"] == 1
