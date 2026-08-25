"""Insight builder for conclusion-first attribution reports."""
from __future__ import annotations

from core.modules.strategy.core.engines.analyzer.insights import build_insights

import pytest

pytestmark = pytest.mark.force_run


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


def test_build_insights_merges_to_two_tiers_and_headline() -> None:
    insights = build_insights(_report_with_rsi_buckets())
    assert insights["status"] == "ok"
    assert insights["field_key"] == "rsi"
    assert len(insights["tiers"]) == 2
    assert "两档" in insights["headline"] or "分水岭" in insights["headline"]
    assert len(insights["key_findings"]) >= 2
    assert insights["explains"]
    assert insights["does_not_explain"]
    assert any("20" in line for line in insights["does_not_explain"])
    assert insights["next_steps"]
    assert insights["technical"]["sample_size"] == 1603


def test_build_insights_empty_without_fields() -> None:
    insights = build_insights(
        {
            "decision_space": {"capture": {}, "declared_core": {}},
            "attribution": {"classical": {"univariate": {"fields": {}}}},
        }
    )
    assert insights["status"] == "empty"
    assert insights["next_steps"]
