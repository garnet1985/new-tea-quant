"""Report narrative: scope_note and hints_for_ui."""
from __future__ import annotations

from core.modules.strategy.core.engines.analyzer.steps.analyze import AnalyzeStep
from core.modules.strategy.core.engines.analyzer.steps.report import ReportStep
from core.modules.strategy.core.engines.analyzer.steps.report.narrative import ReportNarrative

from typing import Optional

import pytest

pytestmark = pytest.mark.force_run


def _build_report(
    source: dict,
    *,
    step: str,
    baseline_source: Optional[dict] = None,
) -> dict:
    analyze_result = AnalyzeStep.run_payload(
        source,
        step=step,
        baseline_source=baseline_source,
    )
    return ReportStep.build(source, analyze_out=analyze_result)


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
    note = ReportNarrative.scope_note("enum")
    assert "机会枚举" in note or "现场" in note
    assert "因果" in note or "预测" in note


def test_report_includes_scope_note_and_hints() -> None:
    report = _build_report(_rsi_like_source(), step="enum")
    classical = report["attribution"]["classical"]
    assert classical["scope_note"]
    hints = report["hints_for_ui"]
    assert len(hints) >= 2
    joined = "\n".join(hints)
    assert "rsi_oversold_threshold" in joined
    assert "对照" in joined
    assert "总胜率" in joined or "总收益" in joined
    assert report["insights"]["headline"]


def test_report_with_baseline_includes_run_comparison() -> None:
    current = _rsi_like_source()
    baseline = _rsi_like_source()
    baseline["version_id"] = "2"
    baseline["inputs"]["declared"]["core"]["rsi_oversold_threshold"] = 25
    for investment in baseline["entities"][0]["investments"]:
        investment["capture"]["rsi_oversold_threshold"] = 25

    report = _build_report(
        current,
        step="enum",
        baseline_source=baseline,
    )
    run_comparison = report["attribution"]["classical"]["run_comparison"]
    assert run_comparison["status"] == "ok"
    assert run_comparison["comparison"]["settings_diff"]
    joined = "\n".join(report["hints_for_ui"])
    assert "对照" in joined
    assert "还没指定对照版本" not in joined


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
    hints = ReportNarrative.hints_for_ui(
        step="enum",
        decision_space={"capture": {"rsi": {"role": "varying"}}, "declared_core": {}},
        attribution=attribution,
    )
    assert any("2 个会变化" in hint or "2 个" in hint for hint in hints)
