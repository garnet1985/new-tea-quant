"""PrepareStep：join 回测产物并写出 source.json。"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.engines.analyzer import Analyzer
from core.modules.strategy.core.engines.analyzer.steps.analyze import AnalyzeStep, DecisionSpaceBuilder
from core.modules.strategy.core.engines.analyzer.steps.prepare import PrepareStep
from core.modules.strategy.core.engines.analyzer.steps.report import ReportStep
from core.modules.strategy.core.services.artifacts import (
    ArtifactStore,
    EntityInvestmentCsv,
    EntitySignalSnapshotCsv,
    EnumerateStore,
    GoalAchievementCsv,
    PriceFactorStore,
    PriceInvestmentRow,
)
from core.modules.strategy.core.services.artifacts.consts import (
    ANALYSIS_REPORT_JSON,
    ANALYSIS_SOURCE_JSON,
    ANALYSIS_SUBDIR,
)
from core.modules.strategy.core.services.artifacts.io import ArtifactIO

pytestmark = pytest.mark.force_run

_EFFECTIVE = {
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


def _build_report(source: dict, *, step: str) -> dict:
    analyze_result = AnalyzeStep.run_payload(source, step=step)
    return ReportStep.build(source, analyze_out=analyze_result)


@pytest.fixture(autouse=True)
def _clear_store_cache():
    ArtifactStore.clear_cache()
    yield
    ArtifactStore.clear_cache()


def _write_runtime(step_dir: Path, *, extra: dict | None = None) -> None:
    runtime = {
        "strategy_key": "demo_rsi",
        "strategy_path": "demo/regression/rsi/rsi_v1_baseline",
        "version_id": 1,
        "market_profile": "china_a_stock",
        "period": {"start_date": "20230101", "end_date": "20260101"},
    }
    if extra:
        runtime.update(extra)
    ArtifactIO.write_json(step_dir / "runtime_env.json", runtime)
    (step_dir / "entity_ids.txt").write_text("688005.SH\n", encoding="utf-8")


def _hydrate_step(step_dir: Path, kind: SimulateKind, *, extra: dict | None = None):
    _write_runtime(step_dir, extra=extra)
    return ArtifactStore.hydrate(
        step_dir,
        kind=kind,
        version_id="1",
        entity_ids=["688005.SH"],
        start_date="20230101",
        end_date="20260101",
        strategy_key="demo_rsi",
        strategy_path="demo/regression/rsi/rsi_v1_baseline",
        market_profile="china_a_stock",
        effective_settings=dict(_EFFECTIVE),
    )


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
    _write_enum_entity(tmp_path)
    store = _hydrate_step(tmp_path, SimulateKind.ENUMERATE)
    source = PrepareStep(store).build()

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
    _write_enum_entity(tmp_path)
    store = _hydrate_step(tmp_path, SimulateKind.ENUMERATE)
    result = Analyzer.run(store)

    source_path = tmp_path / ANALYSIS_SUBDIR / ANALYSIS_SOURCE_JSON
    report_path = tmp_path / ANALYSIS_SUBDIR / ANALYSIS_REPORT_JSON
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
    assert "insights" in report
    assert report["attribution"]["classical"]["run_comparison"]["status"] == "not_requested"
    assert report["decision_space"]["capture"]["rsi"]["role"] == "constant"
    assert report["decision_space"]["capture"]["rsi_length"]["role"] == "constant"
    assert report["decision_space"]["declared_core"]["rsi_oversold_threshold"]["role"] == "settings_knob"


def test_collect_price_joins_enum_capture(tmp_path: Path) -> None:
    enum_dir = tmp_path / "enum" / "1"
    price_dir = tmp_path / "price" / "1"
    enum_dir.mkdir(parents=True)
    price_dir.mkdir(parents=True)

    _write_runtime(enum_dir)
    _write_enum_entity(enum_dir)

    ArtifactIO.write_json(
        price_dir / "runtime_env.json",
        {
            "strategy_key": "demo_rsi",
            "strategy_path": "demo/regression/rsi/rsi_v1_baseline",
            "version_id": 1,
            "enum_version_id": "1",
            "enum_output_dir": str(enum_dir.resolve()),
            "market_profile": "china_a_stock",
            "period": {"start_date": "20230101", "end_date": "20260101"},
        },
    )
    (price_dir / "entity_ids.txt").write_text("688005.SH\n", encoding="utf-8")
    price_store = PriceFactorStore.at(price_dir, version_id="1")
    price_store.write_investments(
        "688005.SH",
        [
            PriceInvestmentRow(
                opportunity_id="1",
                enter_date="20240103",
                enter_price=10.1,
                exit_date="20240201",
                exit_price=11.0,
                roi=0.09,
                holding_days=20,
                holding_trading_days=15,
                exit_reason="take_profit",
                skip_reason="",
                lifecycle="complete",
                result="win",
            ),
            PriceInvestmentRow(
                opportunity_id="2",
                enter_date="20240304",
                enter_price=9.6,
                exit_date="",
                exit_price=0.0,
                roi=0.0,
                holding_days=0,
                holding_trading_days=0,
                exit_reason="",
                skip_reason="liquidity",
                lifecycle="skipped",
                result="",
            ),
        ],
    )

    store = ArtifactStore.hydrate(
        price_dir,
        kind=SimulateKind.PRICE_FACTOR,
        version_id="1",
        entity_ids=["688005.SH"],
        start_date="20230101",
        end_date="20260101",
        strategy_key="demo_rsi",
        strategy_path="demo/regression/rsi/rsi_v1_baseline",
        market_profile="china_a_stock",
        effective_settings=dict(_EFFECTIVE),
    )
    source = PrepareStep(store).build()
    assert source["step"] == "price"
    assert source["upstream"]["enum_version_id"] == "1"
    assert source["inputs"]["capture"]["keys"] == [
        "rsi",
        "rsi_length",
        "rsi_oversold_threshold",
    ]
    assert source["inputs"]["capture"]["coverage"]["investment_count"] == 2
    assert source["inputs"]["capture"]["coverage"]["with_snapshot"] == 1
    rows = source["entities"][0]["investments"]
    assert rows[0]["investment_id"] == "1"
    assert float(rows[0]["capture"]["rsi"]) == 18.2
    assert rows[0]["engine"]["roi"] == 0.09
    assert rows[1]["engine"]["skip_reason"] == "liquidity"
    assert rows[1]["capture"] == {}

    report = _build_report(source, step="price")
    assert report["step"] == "price"
    assert report["manifest"]["outcome_fields"] == ["engine.roi", "engine.result"]
    skip_summary = report["attribution"]["classical"]["skip_summary"]
    assert skip_summary["skipped_count"] == 1
    assert skip_summary["by_reason"]["liquidity"] == 1
    assert report["insights"]["headline"]
    assert any(
        "跳过" in str(item.get("caption") or "")
        for item in report["insights"].get("key_findings") or []
        if isinstance(item, dict)
    )


def test_collect_portfolio_joins_completed_lots(tmp_path: Path) -> None:
    enum_dir = tmp_path / "enum" / "1"
    portfolio_dir = tmp_path / "portfolio" / "1"
    enum_dir.mkdir(parents=True)
    portfolio_dir.mkdir(parents=True)

    _write_runtime(enum_dir)
    _write_enum_entity(enum_dir)

    ArtifactIO.write_json(
        portfolio_dir / "runtime_env.json",
        {
            "strategy_key": "demo_rsi",
            "strategy_path": "demo/regression/rsi/rsi_v1_baseline",
            "version_id": 1,
            "enum_version_id": "1",
            "enum_output_dir": str(enum_dir.resolve()),
            "market_profile": "china_a_stock",
            "period": {"start_date": "20230101", "end_date": "20260101"},
        },
    )
    ArtifactIO.write_json(
        portfolio_dir / "trades.json",
        [
            {
                "date": "20240103",
                "entity_id": "688005.SH",
                "investment_id": "1",
                "side": "buy",
                "shares": 100,
                "price": 10.0,
                "amount": 1000.0,
                "fees": 1.0,
                "total_cost": 1001.0,
            },
            {
                "date": "20240201",
                "entity_id": "688005.SH",
                "investment_id": "1",
                "side": "sell",
                "shares": 100,
                "price": 11.0,
                "amount": 1100.0,
                "fees": 1.0,
                "net_proceeds": 1099.0,
                "profit": 100.0,
            },
            {
                "date": "20240304",
                "entity_id": "688005.SH",
                "investment_id": "2",
                "side": "buy",
                "shares": 50,
                "price": 9.0,
                "amount": 450.0,
                "fees": 1.0,
                "total_cost": 451.0,
            },
            # open buy without sell — should not enter completed lots
        ],
    )
    ArtifactIO.write_json(portfolio_dir / "equity_curve.json", [])

    store = ArtifactStore.hydrate(
        portfolio_dir,
        kind=SimulateKind.PORTFOLIO,
        version_id="1",
        entity_ids=["688005.SH"],
        start_date="20230101",
        end_date="20260101",
        strategy_key="demo_rsi",
        strategy_path="demo/regression/rsi/rsi_v1_baseline",
        market_profile="china_a_stock",
        effective_settings=dict(_EFFECTIVE),
    )
    source = PrepareStep(store).build()
    assert source["step"] == "portfolio"
    assert source["inputs"]["portfolio_artifacts"]["completed_lots"] == 1
    assert source["inputs"]["portfolio_artifacts"]["open_buys"] == 1
    assert source["inputs"]["capture"]["coverage"]["investment_count"] == 1
    assert source["inputs"]["capture"]["coverage"]["with_snapshot"] == 1
    assert source["inputs"]["capture"]["keys"] == [
        "rsi",
        "rsi_length",
        "rsi_oversold_threshold",
    ]
    row = source["entities"][0]["investments"][0]
    assert row["investment_id"] == "1"
    assert float(row["capture"]["rsi"]) == 18.2
    assert row["engine"]["roi"] == pytest.approx(0.1)
    assert row["engine"]["result"] == "win"
    assert row["engine"]["profit"] == 100.0

    report = _build_report(source, step="portfolio")
    assert report["step"] == "portfolio"
    assert report["manifest"]["outcome_fields"] == ["engine.roi", "engine.result"]
    assert report["insights"]["headline"]


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
    report = _build_report(source, step="enum")
    assert report["decision_space"]["capture"]["rsi"]["role"] == "varying"
    assert report["decision_space"]["capture"]["rsi"]["unique_count"] == 2
