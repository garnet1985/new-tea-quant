"""CLI present for analysis/report.json."""
from __future__ import annotations

import io
import json
from pathlib import Path

from core.modules.strategy import Strategy
from core.modules.strategy.core.engines.analyzer import Analyzer

import pytest

pytestmark = pytest.mark.force_run


def _sample_report() -> dict:
    return {
        "schema_version": "1",
        "step": "enum",
        "version_id": "3",
        "strategy_key": "rsi_v1",
        "decision_space": {
            "capture": {
                "rsi": {
                    "role": "varying",
                    "dtype": "numeric",
                    "count": 1603,
                    "unique_count": 80,
                    "min": 5.4,
                    "max": 20.0,
                },
                "rsi_oversold_threshold": {
                    "role": "constant",
                    "dtype": "numeric",
                    "count": 1603,
                    "value": 20.0,
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
                "scope_note": "只描述已触发机会内部差异",
                "univariate": {
                    "status": "ok",
                    "fields": {
                        "rsi": {
                            "n": 1603,
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
                            "correlation": {
                                "status": "ok",
                                "rho": -0.21,
                                "p_value": 1e-5,
                                "n": 1603,
                            },
                        }
                    },
                },
                "multivariate": {
                    "status": "skipped",
                    "reason": "insufficient_varying_fields",
                },
                "run_comparison": {"status": "not_requested"},
            },
            "ml": {"status": "skipped", "reason": "insufficient_varying_fields"},
        },
        "hints_for_ui": [],
    }


def _write_report(tmp_path: Path, payload: dict) -> Path:
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()
    (analysis_dir / "report.json").write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )
    return tmp_path


def test_analysis_report_presenter_is_conclusion_first(tmp_path: Path) -> None:
    _write_report(tmp_path, _sample_report())
    buf = io.StringIO()
    Analyzer.Presenter.load(tmp_path).present(stream=buf)
    text = buf.getvalue()
    assert "一句话结论" in text
    assert text.find("一句话结论") < text.find("证据")
    assert "关键发现" in text
    assert "说明了什么" in text
    assert "建议下一步" in text
    assert "技术细节" in text
    assert text.find("建议下一步") < text.find("技术细节")
    assert "分水岭" in text or "两档" in text


def test_presenter_prefers_persisted_insights(tmp_path: Path) -> None:
    payload = _sample_report()
    payload["insights"] = {
        "status": "ok",
        "headline": "【落盘结论】只应出现这一句",
        "tiers": [],
        "key_findings": [],
        "explains": [],
        "does_not_explain": [],
        "next_steps": [],
        "technical": {},
    }
    _write_report(tmp_path, payload)
    buf = io.StringIO()
    Analyzer.Presenter.load(tmp_path).present(stream=buf)
    text = buf.getvalue()
    assert "【落盘结论】只应出现这一句" in text
    # Must not rebuild from buckets when insights already persisted.
    assert "分水岭" not in text


def test_presenter_shows_run_comparison_section(tmp_path: Path) -> None:
    payload = _sample_report()
    payload["attribution"]["classical"]["run_comparison"] = {
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
                }
            ],
            "capture_diff": [],
            "coverage_diff": [],
        },
    }
    # Force rebuild path (no persisted insights).
    payload.pop("insights", None)
    _write_report(tmp_path, payload)
    buf = io.StringIO()
    Analyzer.Presenter.load(tmp_path).present(stream=buf)
    text = buf.getvalue()
    assert "两次回测对照" in text
    assert "rsi_oversold_threshold" in text
    assert "改了什么" in text
    assert text.find("关键发现") < text.find("两次回测对照")


def test_analysis_report_presenter_missing_report_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Analyzer.Presenter.load(tmp_path)


def test_strategy_present_analysis_report_delegates(tmp_path: Path) -> None:
    _write_report(tmp_path, _sample_report())
    buf = io.StringIO()
    Strategy.present_analysis_report(tmp_path, stream=buf)
    assert "一句话结论" in buf.getvalue()
