"""Run comparison stats implementation."""
from __future__ import annotations

from core.modules.analysis import Analysis, compare_run_summaries

import pytest

pytestmark = pytest.mark.force_run


def _decision_space(
    *,
    threshold: float = 20.0,
    rsi_min: float = 5.0,
    rsi_max: float = 19.0,
    count: int = 100,
) -> dict:
    return {
        "capture": {
            "rsi": {
                "role": "varying",
                "dtype": "numeric",
                "count": count,
                "unique_count": 50,
                "min": rsi_min,
                "max": rsi_max,
            },
            "rsi_oversold_threshold": {
                "role": "constant",
                "dtype": "numeric",
                "count": count,
                "value": threshold,
            },
        },
        "declared_core": {
            "rsi_oversold_threshold": {
                "role": "settings_knob",
                "value": threshold,
                "also_in_capture": True,
                "capture_role": "constant",
            }
        },
    }


def test_compare_run_summaries_detects_settings_and_capture_diff() -> None:
    current = {
        "version_id": "3",
        "decision_space": _decision_space(threshold=20.0, rsi_max=19.0),
        "coverage": {"investment_count": 1603},
    }
    baseline = {
        "version_id": "2",
        "decision_space": _decision_space(threshold=25.0, rsi_max=24.9, count=1400),
        "coverage": {"investment_count": 1400},
    }
    out = compare_run_summaries(current, baseline)
    assert out["status"] == "ok"
    assert out["has_meaningful_diff"] is True
    assert out["settings_diff"][0]["key"] == "rsi_oversold_threshold"
    assert out["settings_diff"][0]["current"] == 20.0
    assert out["settings_diff"][0]["baseline"] == 25.0
    assert any(item["key"] == "rsi" for item in out["capture_diff"])
    assert any(item["key"] == "investment_count" for item in out["coverage_diff"])


def test_compare_run_summaries_no_diff() -> None:
    space = _decision_space()
    summary = {
        "version_id": "3",
        "decision_space": space,
        "coverage": {"investment_count": 100},
    }
    out = compare_run_summaries(summary, dict(summary, version_id="2"))
    assert out["status"] == "ok"
    assert out["has_meaningful_diff"] is False


def test_classical_namespace_delegates_compare() -> None:
    current = {
        "version_id": "1",
        "decision_space": _decision_space(threshold=20.0),
        "coverage": {},
    }
    baseline = {
        "version_id": "0",
        "decision_space": _decision_space(threshold=25.0),
        "coverage": {},
    }
    out = Analysis.Classical.compare_run_summaries(current, baseline)
    assert out["status"] == "ok"
    assert out["settings_diff"]
