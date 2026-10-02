"""枚举层诊断：事实 / 结论 / 建议。"""
from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from core.modules.strategy.core.engines.analyzer.steps.layer import LayerPipeline
from core.modules.strategy.core.engines.shared.enum_result_contract import (
    EnumResult,
    EnumResultsManager,
)
from core.modules.strategy.core.enums import SimulateKind
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.io import ArtifactIO

pytestmark = pytest.mark.force_run


@pytest.fixture(autouse=True)
def _clear_store_cache():
    ArtifactStore.clear_cache()
    yield
    ArtifactStore.clear_cache()


def _result(
    entity_id: str,
    *,
    trigger_date: str,
    exit_reason: str,
    investment_id: str = "1",
    weighted_roi: float = 0.0,
    holding_days: int = 5,
) -> EnumResult:
    return EnumResult(
        entity_id=entity_id,
        investment_id=investment_id,
        trigger_date=trigger_date,
        lifecycle="complete",
        entry_date=trigger_date,
        exit_reason=exit_reason,
        weighted_roi=weighted_roi,
        holding_days=holding_days,
        result="win" if weighted_roi >= 0 else "loss",
    )


def _write_overall(enum_dir: Path, **summary: object) -> None:
    payload = {
        "strategy_key": "demo",
        "strategy_path": "demo",
        "version_id": 1,
        "execution_mode": "entity_based",
        "backtest_period": {"start_date": "20230101", "end_date": "20231231"},
        "summary": {
            "total_opportunities": 0,
            "total_stocks": 20,
            "trigger_stocks": 0,
            "trigger_ratio": 0.0,
            "avg_per_stock": 0.0,
            "completed_count": 0,
            "unfinished_count": 0,
            "completed_ratio": 1.0,
            "mean_gap": 0.0,
            "cv": 0.0,
            "dispersion_conclusion": "均匀",
        },
    }
    payload["summary"].update(summary)
    ArtifactIO.write_json(enum_dir / "overall_report.json", payload)


def _enum_store(
    tmp_path: Path,
    rows_by_entity: dict[str, list[EnumResult]],
    *,
    summary: dict | None = None,
    goal: dict | None = None,
) -> ArtifactStore:
    version_dir = tmp_path / "simulations" / "1"
    enum_dir = version_dir / "enum"
    enum_dir.mkdir(parents=True)
    manager = EnumResultsManager.at(enum_dir)
    for eid, rows in rows_by_entity.items():
        manager.accept(eid, rows)
    manager.persist()
    total = sum(len(rows) for rows in rows_by_entity.values())
    trigger = len(rows_by_entity)
    merged = {
        "total_opportunities": total,
        "trigger_stocks": trigger,
        "trigger_ratio": trigger / 20.0,
        "avg_per_stock": round(total / trigger, 2) if trigger else 0.0,
        "completed_count": total,
        "completed_ratio": 1.0,
    }
    if summary:
        merged.update(summary)
    _write_overall(enum_dir, **merged)
    if goal is not None:
        ArtifactIO.write_json(
            version_dir / "effective_settings.json",
            {"goal": goal},
        )
    return ArtifactStore.hydrate(
        enum_dir,
        kind=SimulateKind.ENUMERATE,
        version_id="1",
        entity_ids=list(rows_by_entity),
        start_date="20230101",
        end_date="20231231",
        strategy_key="demo",
    )


def test_enumerate_layer_reports_concentration_and_stop_loss(tmp_path, capsys):
    rows = {
        "AAA.SH": [
            _result("AAA.SH", trigger_date=f"202301{day:02d}", exit_reason="stop_loss", investment_id=str(day), weighted_roi=-0.1)
            for day in range(1, 11)
        ],
        "BBB.SH": [
            _result("BBB.SH", trigger_date="20230115", exit_reason="stop_loss", weighted_roi=-0.08),
            _result("BBB.SH", trigger_date="20230120", exit_reason="take_profit", investment_id="2", weighted_roi=0.2),
        ],
    }
    store = _enum_store(
        tmp_path,
        rows,
        summary={"cv": 0.9, "dispersion_conclusion": "较集中"},
        goal={"take_profit": {"stages": [{"ratio": 0.2, "close_invest": True}]}},
    )
    report = LayerPipeline.run(store, present=True, force=True)
    assert report["success"] is True
    assert report["layer"] == "enumerate"
    facts = report["facts"]
    assert facts["quantity"]["total_opportunities"] == 12
    assert facts["quantity"]["top5_share"] == 1.0
    assert facts["time"]["calendar"]["peak_share"] == 1.0
    assert facts["exits"]["stop_loss_share"] == pytest.approx(11 / 12, abs=0.001)
    assert facts["leftover_upside"]["measurable"] is False
    assert facts["leftover_upside"]["mode"] == "single_close"
    ids = {item["id"] for item in report["conclusions"]}
    assert "stock_concentrated" in ids
    assert "calendar_clustered" in ids
    assert "stop_loss_heavy" in ids
    assert "gates_need_overlay" in ids
    assert "leftover_not_measurable" in ids
    suggestion_ids = {item["id"] for item in report["suggestions"]}
    assert "gates_need_overlay" in suggestion_ids
    assert store.file("layer_attribution").is_file()
    printed = capsys.readouterr().out
    assert "事实" in printed
    assert "结论" in printed
    assert "建议" in printed
    assert "纸面结局" in printed


def test_enumerate_layer_skips_when_report_exists(tmp_path):
    store = _enum_store(
        tmp_path,
        {"AAA.SH": [_result("AAA.SH", trigger_date="20230101", exit_reason="take_profit")]},
    )
    LayerPipeline.run(store, present=False, force=True)
    store.write_json(
        "layer_attribution",
        {"layer": "enumerate", "facts": {"marker": True}, "conclusions": [], "suggestions": []},
    )
    again = LayerPipeline.run(store, present=False, force=False)
    assert again.get("facts", {}).get("marker") is True
    assert again.get("reason") == "exists"


def test_leftover_measurable_with_staged_take_profit(tmp_path):
    store = _enum_store(
        tmp_path,
        {"AAA.SH": [_result("AAA.SH", trigger_date="20230101", exit_reason="take_profit")]},
        goal={
            "take_profit": {
                "stages": [
                    {"ratio": 0.2, "exit_ratio": 0.5},
                    {"ratio": 0.4, "close_invest": True},
                ]
            }
        },
    )
    report = LayerPipeline.run(store, present=False, force=True)
    assert report["facts"]["leftover_upside"]["measurable"] is True
    assert report["facts"]["leftover_upside"]["mode"] == "staged"
    ids = {item["id"] for item in report["conclusions"]}
    assert "leftover_not_measurable" not in ids


def test_layer_presenter_three_blocks():
    from core.modules.strategy.core.engines.analyzer.steps.layer.present import LayerPresenter

    stream = StringIO()
    LayerPresenter(
        {
            "layer": "enumerate",
            "version_id": "4",
            "disclaimer": "纸面结局",
            "facts": {
                "quantity": {
                    "total_opportunities": 18,
                    "total_stocks": 100,
                    "trigger_stocks": 12,
                    "trigger_ratio": 0.12,
                    "top5_share": 0.4,
                },
                "time": {
                    "calendar": {"peak_month": "2023-01", "peak_share": 0.3},
                    "per_stock": {"cv": 0.5, "dispersion_conclusion": "中等聚集"},
                },
                "exits": {
                    "by_reason": [
                        {"reason": "stop_loss", "label": "止损", "count": 8, "share": 0.44}
                    ]
                },
                "leftover_upside": {"measurable": False, "mode": "single_close"},
            },
            "conclusions": [{"id": "x", "text": "机会偏少"}],
            "suggestions": [{"id": "y", "text": "写 overlays"}],
        }
    ).present(stream)
    text = stream.getvalue()
    assert "事实" in text
    assert "结论" in text
    assert "建议" in text
    assert "机会偏少" in text
    assert "写 overlays" in text
