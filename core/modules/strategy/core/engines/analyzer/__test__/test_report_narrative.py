"""Report narrative: scope_note and hints_for_ui."""
from __future__ import annotations

from core.modules.strategy.core.engines.analyzer.report import AttributionReportBuilder
from core.modules.strategy.core.engines.analyzer.report_narrative import (
    build_hints_for_ui,
    build_scope_note,
)

import pytest

pytestmark = pytest.mark.force_run


def _rsi_like_source() -> dict:
    investments = []
    for i in range(1, 36):
        investments.append(
            {
                "investment_id": str(i),
                "capture": {
                    "rsi": 10.0 + (i % 10),
                    "rsi_length": 14,
                    "rsi_oversold_threshold": 20,
                },
                "engine": {
                    "weighted_roi": 0.01 * (i % 7) - 0.02,
                    "result": "win" if i % 2 else "loss",
                },
            }
        )
    return {
        "version_id": "3",
        "strategy_key": "rsi_v1",
        "inputs": {
            "capture": {
                "keys": ["rsi", "rsi_length", "rsi_oversold_threshold"],
                "coverage": {"investment_count": 35},
            },
            "declared": {"core": {"rsi_oversold_threshold": 20}},
        },
        "entities": [{"entity_id": "688005.SH", "investments": investments}],
    }


def test_build_scope_note_enum() -> None:
    note = build_scope_note("enum")
    assert "in-sample" in note or "共变" in note
    assert "overall" in note


def test_report_includes_scope_note_and_hints() -> None:
    report = AttributionReportBuilder.build(_rsi_like_source(), step="enum")
    classical = report["attribution"]["classical"]
    assert classical["scope_note"]
    hints = report["hints_for_ui"]
    assert len(hints) >= 2
    joined = "\n".join(hints)
    assert "rsi_oversold_threshold" in joined
    assert "run_comparison" in joined
    assert "overall_report" in joined


def test_report_with_baseline_includes_run_comparison() -> None:
    current = _rsi_like_source()
    baseline = _rsi_like_source()
    baseline["version_id"] = "2"
    baseline["inputs"]["declared"]["core"]["rsi_oversold_threshold"] = 25
    for investment in baseline["entities"][0]["investments"]:
        investment["capture"]["rsi_oversold_threshold"] = 25

    report = AttributionReportBuilder.build(
        current,
        step="enum",
        baseline_source=baseline,
    )
    run_comparison = report["attribution"]["classical"]["run_comparison"]
    assert run_comparison["status"] == "ok"
    assert run_comparison["comparison"]["settings_diff"]
    joined = "\n".join(report["hints_for_ui"])
    assert "run_comparison" in joined
    assert "未指定 baseline version" not in joined


def test_hints_for_multivariate_skip() -> None:
    attribution = {
        "classical": {
            "status": "ok",
            "multivariate": {
                "status": "skipped",
                "reason": "insufficient_varying_fields",
                "found_features": 1,
            },
            "run_comparison": {"status": "not_requested"},
            "univariate": {"status": "ok", "fields": {"rsi": {}}},
        },
        "ml": {"status": "skipped", "reason": "insufficient_varying_fields"},
    }
    hints = build_hints_for_ui(
        step="enum",
        decision_space={"capture": {"rsi": {"role": "varying"}}, "declared_core": {}},
        attribution=attribution,
    )
    assert any("2 个 varying" in hint for hint in hints)
