"""AttributionInputCollector：join investments / goals / snapshots。"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.engines.analyzer.collector import AttributionInputCollector
from core.modules.strategy.core.engines.analyzer.consts import REPORT_JSON, SOURCE_JSON
from core.modules.strategy.core.engines.analyzer.pipeline import AnalyzerPipeline
from core.modules.strategy.core.engines.analyzer.report import AttributionReportBuilder
from core.modules.strategy.core.services.artifacts import (
    ArtifactStore,
    EntityInvestmentCsv,
    EntitySignalSnapshotCsv,
    EnumerateStore,
    GoalAchievementCsv,
)
from core.modules.strategy.core.services.artifacts.io import ArtifactIO

pytestmark = pytest.mark.force_run


@pytest.fixture(autouse=True)
def _clear_store_cache():
    ArtifactStore.clear_cache()
    yield
    ArtifactStore.clear_cache()


def _write_runtime(tmp_path: Path, *, kind: SimulateKind) -> None:
    runtime = {
        "strategy_key": "demo_rsi",
        "strategy_path": "demo/regression/rsi/rsi_v1_baseline",
        "version_id": 1,
        "fingerprints": {"settings": "abc", "env": "def"},
        "period": {"start_date": "20230101", "end_date": "20260101"},
        "settings": {
            "effective_settings": {
                "core": {"rsi_oversold_threshold": 20},
                "data": {
                    "base": {
                        "data_key": "stock.kline.daily",
                        "indicators": {"rsi": [{"length": 14}]},
                    }
                },
                "goal": {"stop_loss": {"stages": [{"ratio": -0.2}]}},
                "simulation": {"execution": {"mode": "entity_based"}},
            }
        },
    }
    ArtifactIO.write_json(tmp_path / "runtime_env.json", runtime)
    (tmp_path / "entity_ids.txt").write_text("688005.SH\n", encoding="utf-8")


def _write_enum_entity(tmp_path: Path) -> None:
    entities = tmp_path / "entities"
    entities.mkdir(parents=True, exist_ok=True)
    store = EnumerateStore.at(tmp_path, version_id="1")
    store.write_investments(
        EntityInvestmentCsv.build(
            "688005.SH",
            [
                {
                    "meta": {"opportunity_id": "1"},
                    "trigger_date": "20240102",
                    "trigger_price": 10.0,
                    "lifecycle": "complete",
                    "entry": {"date": "20240103", "price": 10.1},
                    "exit_info": {
                        "date": "20240201",
                        "price": 11.0,
                        "reason": "take_profit",
                    },
                    "holding": {"days": 20},
                    "outcome": {"result": "win", "weighted_roi": 0.08},
                    "signal_snapshot": {
                        "rsi": 18.2,
                        "rsi_length": 14,
                        "rsi_oversold_threshold": 20,
                    },
                },
                {
                    "meta": {"opportunity_id": "2"},
                    "trigger_date": "20240301",
                    "trigger_price": 9.5,
                    "lifecycle": "complete",
                    "entry": {"date": "20240304", "price": 9.6},
                    "exit_info": {
                        "date": "20240401",
                        "price": 9.0,
                        "reason": "stop_loss",
                    },
                    "holding": {"days": 18},
                    "outcome": {"result": "loss", "weighted_roi": -0.05},
                },
            ],
        )
    )
    store.write_goals(
        GoalAchievementCsv.build(
            "688005.SH",
            [
                {
                    "meta": {"opportunity_id": "1"},
                    "trigger_date": "20240102",
                    "trigger_price": 10.0,
                    "lifecycle": "complete",
                    "entry": {},
                    "exit_info": {},
                    "holding": {},
                    "outcome": {},
                    "completed_goals": [
                        {
                            "name": "take_profit",
                            "date": "20240201",
                            "price": 11.0,
                            "exit_ratio": 0.5,
                            "profit": 0.4,
                            "weighted_profit": 0.2,
                            "reason": "take_profit",
                            "roi": 0.08,
                        }
                    ],
                }
            ],
        )
    )
    store.write_snapshots(
        EntitySignalSnapshotCsv.build(
            "688005.SH",
            [
                {
                    "meta": {"opportunity_id": "1"},
                    "trigger_date": "20240102",
                    "trigger_price": 10.0,
                    "lifecycle": "complete",
                    "entry": {},
                    "exit_info": {},
                    "holding": {},
                    "outcome": {},
                    "signal_snapshot": {
                        "rsi": 18.2,
                        "rsi_length": 14,
                        "rsi_oversold_threshold": 20,
                    },
                },
                {
                    "meta": {"opportunity_id": "2"},
                    "trigger_date": "20240301",
                    "trigger_price": 9.5,
                    "lifecycle": "complete",
                    "entry": {},
                    "exit_info": {},
                    "holding": {},
                    "outcome": {},
                },
            ],
        )
    )


def test_collect_enum_joins_capture_and_goal_legs(tmp_path: Path) -> None:
    _write_runtime(tmp_path, kind=SimulateKind.ENUMERATE)
    _write_enum_entity(tmp_path)

    store = EnumerateStore.open(tmp_path, version_id="1")
    source = AttributionInputCollector(store).collect()

    assert source["step"] == "enum"
    assert source["inputs"]["declared"]["core"]["rsi_oversold_threshold"] == 20
    assert source["inputs"]["capture"]["keys"] == [
        "rsi",
        "rsi_length",
        "rsi_oversold_threshold",
    ]
    assert source["inputs"]["capture"]["coverage"] == {
        "investment_count": 2,
        "with_snapshot": 1,
    }

    rows = source["entities"][0]["investments"]
    assert rows[0]["investment_id"] == "1"
    assert float(rows[0]["capture"]["rsi"]) == 18.2
    assert rows[0]["goal_legs"][0]["goal_name"] == "take_profit"
    assert rows[1]["capture"] == {}


def test_pipeline_writes_source_and_report_json(tmp_path: Path) -> None:
    _write_runtime(tmp_path, kind=SimulateKind.ENUMERATE)
    _write_enum_entity(tmp_path)

    store = EnumerateStore.open(tmp_path, version_id="1")
    result = AnalyzerPipeline.run(store)

    source_path = tmp_path / "analysis" / SOURCE_JSON
    report_path = tmp_path / "analysis" / REPORT_JSON
    assert source_path.is_file()
    assert report_path.is_file()
    assert result["step"] == "enum"
    assert result["investment_count"] == 2
    payload = ArtifactIO.read_json(source_path)
    assert payload["schema_version"] == "1"
    assert payload["step"] == "enum"
    assert "collected_at" in payload

    report = ArtifactIO.read_json(report_path)
    assert report["step"] == "enum"
    assert "attribution" in report
    assert report["attribution"]["classical"]["run_comparison"]["status"] == "not_requested"
    assert report["decision_space"]["capture"]["rsi"]["role"] == "constant"
    assert report["decision_space"]["capture"]["rsi_length"]["role"] == "constant"
    assert report["decision_space"]["declared_core"]["rsi_oversold_threshold"]["role"] == "settings_knob"


def test_report_marks_varying_capture() -> None:
    source = {
        "version_id": "1",
        "strategy_key": "demo",
        "inputs": {
            "capture": {"keys": ["rsi"], "coverage": {}},
            "declared": {"core": {}},
        },
        "entities": [
            {
                "entity_id": "688005.SH",
                "investments": [
                    {"investment_id": "1", "capture": {"rsi": 18.0}},
                    {"investment_id": "2", "capture": {"rsi": 19.5}},
                ],
            }
        ],
    }
    report = AttributionReportBuilder.build(source, step="enum")
    assert report["decision_space"]["capture"]["rsi"]["role"] == "varying"
    assert report["decision_space"]["capture"]["rsi"]["unique_count"] == 2
