"""滚动对照：配置、区间重叠、相对基准的差值。"""
from io import StringIO
from pathlib import Path

import pytest

from core.modules.strategy.core.engines.rolling.config import load_rolling_windows
from core.modules.strategy.core.engines.rolling.present import RollingPresenter
from core.modules.strategy.core.engines.rolling.report import (
    assemble_report,
    compare_window,
    window_span,
)


def test_load_rolling_windows_rejects_duplicates(tmp_path: Path) -> None:
    path = tmp_path / "rolling.py"
    path.write_text(
        "rolling = {'windows': ["
        "{'start': '20240101', 'end': '20241231'},"
        "{'start': '20240101', 'end': '20241231'}"
        "]}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="重复"):
        load_rolling_windows(tmp_path)


def test_load_rolling_windows(tmp_path: Path) -> None:
    (tmp_path / "rolling.py").write_text(
        "rolling = {'windows': ["
        "{'start': '20240101', 'end': '20241231'},"
        "{'start': '20250101', 'end': '20251231'}"
        "]}\n",
        encoding="utf-8",
    )
    windows = load_rolling_windows(tmp_path)
    assert windows == (
        {"start": "20240101", "end": "20241231"},
        {"start": "20250101", "end": "20251231"},
    )


def test_window_span_counts_overlap() -> None:
    span = window_span("20240101", "20241231", "20230101", "20231231")
    assert span["overlap_days"] == 0
    assert span["length_days"] == 366
    nested = window_span("20230601", "20240630", "20230101", "20231231")
    assert nested["overlap_days"] == 214


def test_compare_window_skips_total_return_delta() -> None:
    baseline = {
        "layers": {
            "enum": {"total_opportunities": 10, "trigger_stocks": 4, "cv": 0.2},
            "price": {"win_rate": 50.0, "avg_roi": 0.1, "top5_trade_profit_share": 0.4},
            "portfolio": {
                "max_drawdown": 0.2,
                "sharpe_ratio": 1.0,
                "sortino_ratio": 1.2,
                "calmar_ratio": 0.5,
                "total_return": 0.3,
            },
        },
        "dispersion_conclusion": "分散",
    }
    window = {
        "layers": {
            "enum": {"total_opportunities": 8, "trigger_stocks": 3, "cv": 0.5},
            "price": {"win_rate": 40.0, "avg_roi": 0.05, "top5_trade_profit_share": 0.7},
            "portfolio": {
                "max_drawdown": 0.25,
                "sharpe_ratio": 0.4,
                "sortino_ratio": 0.5,
                "calmar_ratio": 0.2,
                "total_return": 0.1,
            },
        },
        "dispersion_conclusion": "集中",
    }
    row = compare_window(
        baseline,
        window,
        version_id="1-s1",
        start="20240101",
        end="20241231",
        baseline_start="20230101",
        baseline_end="20231231",
    )
    portfolio = row["layers"]["portfolio"]
    assert "delta" not in portfolio["total_return"]
    assert portfolio["total_return"]["value"] == pytest.approx(0.1)
    assert portfolio["sharpe_ratio"]["delta"] == pytest.approx(-0.6)
    assert row["layers"]["enum"]["total_opportunities"]["delta"] == -2
    assert row["overlap_days"] == 0
    assert row["dispersion_conclusion"] == "集中"


def test_report_keeps_baseline_row() -> None:
    report = assemble_report(
        parent_version_id="1",
        baseline_start="20230101",
        baseline_end="20231231",
        baseline_metrics={
            "layers": {
                "enum": {"total_opportunities": 71, "trigger_stocks": 60, "cv": 0.54},
                "price": {"win_rate": 49.3, "avg_roi": 0.0039, "top5_trade_profit_share": 0.1},
                "portfolio": {
                    "max_drawdown": 0.08,
                    "sharpe_ratio": 0.11,
                    "sortino_ratio": 0.17,
                    "calmar_ratio": 0.25,
                    "total_return": 0.05,
                },
            },
            "dispersion_conclusion": "中等聚集",
        },
        windows=[],
    )
    assert report["baseline"]["label"] == "20230101-20231231"
    assert report["baseline"]["layers"]["enum"]["total_opportunities"]["value"] == 71
    buf = StringIO()
    RollingPresenter.load(report).present(stream=buf)
    text = buf.getvalue()
    assert "20230101-20231231" in text
    assert "71" in text
