"""AttributionPipeline integration (stub analysis backends)."""
from __future__ import annotations

from core.modules.strategy.core.engines.analyzer.attribution_pipeline import (
    AttributionPipeline,
)
from core.modules.strategy.core.engines.analyzer.report import AttributionReportBuilder
from core.modules.strategy.core.engines.analyzer.stages.base import AttributionContext

import pytest

pytestmark = pytest.mark.force_run


def _varying_source() -> dict:
    investments = []
    for i in range(1, 36):
        rsi = 10.0 + (i % 10)
        investments.append(
            {
                "investment_id": str(i),
                "capture": {"rsi": rsi},
                "engine": {
                    "weighted_roi": 0.01 * (i % 7) - 0.02,
                    "result": "win" if i % 2 else "loss",
                },
            }
        )
    return {
        "version_id": "1",
        "strategy_key": "demo",
        "inputs": {
            "capture": {"keys": ["rsi"], "coverage": {"investment_count": 35}},
            "declared": {"core": {}},
        },
        "entities": [{"entity_id": "688005.SH", "investments": investments}],
    }


def test_attribution_pipeline_univariate_ok() -> None:
    source = _varying_source()
    decision_space = AttributionReportBuilder._decision_space(source)
    assert decision_space["capture"]["rsi"]["role"] == "varying"

    out = AttributionPipeline.run(
        AttributionContext(source=source, step="enum", decision_space=decision_space)
    )
    classical = out["classical"]
    assert classical["status"] == "ok"
    assert "univariate" in classical
    rsi = classical["univariate"]["fields"]["rsi"]
    assert rsi["buckets"]["status"] == "ok"
    assert len(rsi["buckets"]["buckets"]) >= 1
    assert rsi["correlation"]["status"] == "ok"
    assert classical["multivariate"]["status"] == "skipped"
    assert classical["run_comparison"]["status"] == "not_requested"
    assert out["ml"]["status"] == "skipped"


def _multivariate_source() -> dict:
    investments = []
    for i in range(1, 221):
        investments.append(
            {
                "investment_id": str(i),
                "capture": {
                    "feat_a": 10.0 + (i % 11),
                    "feat_b": 0.5 + (i % 7) * 0.1,
                },
                "engine": {
                    "weighted_roi": 0.002 * (10.0 + (i % 11)) - 0.01 * (0.5 + (i % 7) * 0.1),
                    "result": "win" if i % 3 else "loss",
                },
            }
        )
    return {
        "version_id": "1",
        "strategy_key": "demo",
        "inputs": {
            "capture": {
                "keys": ["feat_a", "feat_b"],
                "coverage": {"investment_count": 220},
            },
            "declared": {"core": {}},
        },
        "entities": [{"entity_id": "688005.SH", "investments": investments}],
    }


def test_attribution_pipeline_multivariate_ok() -> None:
    source = _multivariate_source()
    decision_space = AttributionReportBuilder._decision_space(source)
    assert len(decision_space["capture"]) == 2

    out = AttributionPipeline.run(
        AttributionContext(source=source, step="enum", decision_space=decision_space)
    )
    multivariate = out["classical"]["multivariate"]
    assert multivariate["status"] == "ok"
    assert multivariate["logistic_win"]["status"] == "ok"
    assert multivariate["ols_weighted_roi"]["status"] == "ok"
    assert len(multivariate["logistic_win"]["coefficients"]) == 2


def test_attribution_pipeline_ml_ok() -> None:
    source = _multivariate_source_large()
    decision_space = AttributionReportBuilder._decision_space(source)

    out = AttributionPipeline.run(
        AttributionContext(source=source, step="enum", decision_space=decision_space)
    )
    ml = out["ml"]
    assert ml["status"] in ("ok", "partial")
    assert ml["xgb"]["status"] in ("ok", "partial")
    assert len(ml["xgb"]["feature_importance"]) == 2


def _multivariate_source_large() -> dict:
    investments = []
    for i in range(1, 521):
        investments.append(
            {
                "investment_id": str(i),
                "capture": {
                    "feat_a": 10.0 + (i % 11),
                    "feat_b": 0.5 + (i % 7) * 0.1,
                },
                "engine": {
                    "weighted_roi": 0.002 * (10.0 + (i % 11)) - 0.01 * (0.5 + (i % 7) * 0.1),
                    "result": "win" if i % 3 else "loss",
                },
            }
        )
    return {
        "version_id": "1",
        "strategy_key": "demo",
        "inputs": {
            "capture": {
                "keys": ["feat_a", "feat_b"],
                "coverage": {"investment_count": 520},
            },
            "declared": {"core": {}},
        },
        "entities": [{"entity_id": "688005.SH", "investments": investments}],
    }


def test_report_includes_attribution_section() -> None:
    source = _varying_source()
    report = AttributionReportBuilder.build(source, step="enum")
    assert "attribution" in report
    corr = report["attribution"]["classical"]["univariate"]["fields"]["rsi"]["correlation"]
    assert corr["status"] == "ok"
    assert corr["rho"] is not None
    assert report["attribution"]["classical"]["scope_note"]
    assert len(report["hints_for_ui"]) >= 1


def test_attribution_pipeline_run_comparison_ok() -> None:
    current_source = _rsi_like_source_for_compare(current_threshold=20.0, version_id="3")
    baseline_source = _rsi_like_source_for_compare(current_threshold=25.0, version_id="2")
    decision_space = AttributionReportBuilder._decision_space(current_source)
    baseline_decision_space = AttributionReportBuilder._decision_space(baseline_source)

    out = AttributionPipeline.run(
        AttributionContext(
            source=current_source,
            step="enum",
            decision_space=decision_space,
            baseline_source=baseline_source,
            baseline_decision_space=baseline_decision_space,
        )
    )
    run_comparison = out["classical"]["run_comparison"]
    assert run_comparison["status"] == "ok"
    comparison = run_comparison["comparison"]
    assert comparison["has_meaningful_diff"] is True
    assert comparison["settings_diff"][0]["key"] == "rsi_oversold_threshold"


def _rsi_like_source_for_compare(*, current_threshold: float, version_id: str) -> dict:
    investments = []
    for i in range(1, 36):
        investments.append(
            {
                "investment_id": str(i),
                "capture": {
                    "rsi": 10.0 + (i % 10),
                    "rsi_length": 14,
                    "rsi_oversold_threshold": current_threshold,
                },
                "engine": {
                    "weighted_roi": 0.01 * (i % 7) - 0.02,
                    "result": "win" if i % 2 else "loss",
                },
            }
        )
    return {
        "version_id": version_id,
        "strategy_key": "rsi_v1",
        "inputs": {
            "capture": {
                "keys": ["rsi", "rsi_length", "rsi_oversold_threshold"],
                "coverage": {"investment_count": 35},
            },
            "declared": {"core": {"rsi_oversold_threshold": current_threshold}},
        },
        "entities": [{"entity_id": "688005.SH", "investments": investments}],
    }
