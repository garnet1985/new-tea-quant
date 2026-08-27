"""UI facts payload: structured fields, no CLI narrative copy."""
from __future__ import annotations

import json
from pathlib import Path

from core.modules.strategy.core.engines.analyzer.steps.report import (
    InsightBuilder,
    InsightFacts,
    ReportStep,
)

import pytest

pytestmark = pytest.mark.force_run

_NARRATIVE_KEYS = frozenset(
    {"headline", "chart_note", "next_steps", "explains", "does_not_explain", "caption"}
)


def _report_with_rsi_buckets() -> dict:
    return {
        "strategy_key": "rsi_v1",
        "step": "enum",
        "version_id": "3",
        "decision_space": {
            "capture": {
                "rsi": {
                    "role": "varying",
                    "min": 5.4,
                    "max": 20.0,
                    "count": 1603,
                },
                "rsi_oversold_threshold": {
                    "role": "constant",
                    "value": 20.0,
                    "count": 1603,
                },
            },
            "declared_core": {
                "rsi_oversold_threshold": {
                    "role": "settings_knob",
                    "value": 20,
                    "also_in_capture": True,
                    "capture_role": "constant",
                }
            },
        },
        "attribution": {
            "classical": {
                "status": "ok",
                "scope_note": "test",
                "skip_summary": {
                    "investment_count": 1603,
                    "skipped_count": 12,
                    "by_reason": {"liquidity": 12},
                },
                "univariate": {
                    "status": "ok",
                    "fields": {
                        "rsi": {
                            "n": 1603,
                            "correlation": {
                                "status": "ok",
                                "rho": -0.21,
                                "p_value": 1e-10,
                            },
                            "buckets": {
                                "status": "ok",
                                "buckets": [
                                    {
                                        "label": "Q1",
                                        "range": {"min": 5.4, "max": 13.8},
                                        "count": 320,
                                        "win_rate": 0.69,
                                        "mean_roi": 0.116,
                                    },
                                    {
                                        "label": "Q2",
                                        "range": {"min": 13.8, "max": 16.2},
                                        "count": 321,
                                        "win_rate": 0.71,
                                        "mean_roi": 0.104,
                                    },
                                    {
                                        "label": "Q3",
                                        "range": {"min": 16.2, "max": 17.9},
                                        "count": 320,
                                        "win_rate": 0.60,
                                        "mean_roi": 0.069,
                                    },
                                    {
                                        "label": "Q4",
                                        "range": {"min": 17.9, "max": 19.0},
                                        "count": 321,
                                        "win_rate": 0.52,
                                        "mean_roi": 0.015,
                                    },
                                    {
                                        "label": "Q5",
                                        "range": {"min": 19.0, "max": 20.0},
                                        "count": 321,
                                        "win_rate": 0.55,
                                        "mean_roi": 0.032,
                                    },
                                ],
                            },
                        }
                    },
                },
            }
        },
    }


def _assert_no_narrative(payload) -> None:
    if isinstance(payload, dict):
        overlap = _NARRATIVE_KEYS.intersection(payload.keys())
        assert not overlap, f"narrative keys in facts: {sorted(overlap)}"
        for value in payload.values():
            _assert_no_narrative(value)
    elif isinstance(payload, list):
        for item in payload:
            _assert_no_narrative(item)


def test_facts_from_report_has_field_tiers_correlation() -> None:
    facts = InsightFacts.from_report(_report_with_rsi_buckets())
    assert facts["status"] == "ok"
    assert facts["field_key"] == "rsi"
    assert len(facts["buckets"]) == 5
    assert len(facts["tiers"]) == 2
    assert facts["correlation"]["rho"] == -0.21
    assert facts["skip_summary"]["skipped_count"] == 12
    _assert_no_narrative(facts)


def test_facts_empty_without_fields() -> None:
    facts = InsightFacts.from_report(
        {
            "decision_space": {"capture": {}, "declared_core": {}},
            "attribution": {"classical": {"univariate": {"fields": {}}}},
        }
    )
    assert facts["status"] == "empty"
    assert facts["field_key"] is None
    assert facts["tiers"] == []
    assert facts["buckets"] == []
    assert facts["empty_reason"]["code"] == "unknown"
    assert facts["empty_reason"]["investment_count"] == 0
    assert facts["empty_reason"]["with_snapshot"] == 0
    _assert_no_narrative(facts)


def test_facts_empty_no_capture() -> None:
    facts = InsightFacts.from_report(
        {
            "manifest": {
                "capture_keys": [],
                "coverage": {"investment_count": 141, "with_snapshot": 0},
            },
            "decision_space": {"capture": {}, "declared_core": {}},
            "attribution": {
                "classical": {
                    "univariate": {
                        "status": "skipped",
                        "reason": "no_varying_numeric_capture",
                        "fields": {},
                    }
                }
            },
        }
    )
    assert facts["status"] == "empty"
    assert facts["empty_reason"]["code"] == "no_capture"
    assert facts["empty_reason"]["investment_count"] == 141
    assert facts["empty_reason"]["with_snapshot"] == 0
    assert facts["empty_reason"]["capture_key_count"] == 0
    _assert_no_narrative(facts)


def test_facts_empty_insufficient_samples() -> None:
    facts = InsightFacts.from_report(
        {
            "manifest": {
                "capture_keys": ["rsi"],
                "coverage": {"investment_count": 5, "with_snapshot": 1},
            },
            "attribution": {
                "classical": {
                    "univariate": {
                        "status": "skipped",
                        "reason": "insufficient_samples",
                        "fields": {
                            "rsi": {"reason": "insufficient_samples", "n": 1},
                        },
                    }
                }
            },
        }
    )
    assert facts["status"] == "empty"
    assert facts["empty_reason"]["code"] == "insufficient_samples"
    assert facts["empty_reason"]["investment_count"] == 5
    assert facts["empty_reason"]["with_snapshot"] == 1
    _assert_no_narrative(facts)


def test_facts_run_comparison_and_multivariate_are_structured() -> None:
    report = _report_with_rsi_buckets()
    report["attribution"]["classical"]["run_comparison"] = {
        "status": "ok",
        "baseline_version_id": "2",
        "comparison": {
            "status": "ok",
            "current_version_id": "3",
            "baseline_version_id": "2",
            "has_meaningful_diff": True,
            "settings_diff": [
                {
                    "key": "rsi_oversold_threshold",
                    "current": 20,
                    "baseline": 25,
                    "role": "settings_knob",
                }
            ],
        },
    }
    report["attribution"]["classical"]["multivariate"] = {
        "status": "ok",
        "features": ["rsi"],
        "n": 1603,
        "ols_weighted_roi": {
            "status": "ok",
            "coefficients": [{"feature": "rsi", "coef": -0.02}],
        },
        "logistic_win": {"status": "skipped"},
    }
    facts = InsightFacts.from_report(report)
    assert facts["run_comparison"]["status"] == "ok"
    assert facts["run_comparison"]["settings_diff"][0]["key"] == "rsi_oversold_threshold"
    assert facts["multivariate"]["ranking"][0]["key"] == "rsi"
    assert facts["multivariate"]["ranking"][0]["coef"] == -0.02
    _assert_no_narrative(facts)


def test_load_payload_exposes_facts_and_keeps_insights(tmp_path: Path) -> None:
    report = _report_with_rsi_buckets()
    report["insights"] = InsightBuilder.build(report)
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()
    (analysis_dir / "report.json").write_text(json.dumps(report), encoding="utf-8")

    payload = ReportStep.load_payload(tmp_path)
    assert payload["available"] is True
    assert payload["facts"]["field_key"] == "rsi"
    assert payload["insights"]["headline"]
    _assert_no_narrative(payload["facts"])


def test_load_payload_missing_report(tmp_path: Path) -> None:
    payload = ReportStep.load_payload(tmp_path)
    assert payload["available"] is False
    assert payload["facts"] is None
    assert payload["insights"] is None
