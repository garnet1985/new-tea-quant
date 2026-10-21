"""normalize / analyze / runner（不连库）。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.modules.series_relation.core.pipeline.analyze import (
    MIN_OVERLAP_REPORT,
    pairwise_summary,
)
from core.modules.series_relation.core.pipeline.normalize import normalize_points
from core.modules.series_relation.core.pipeline.runner import run_relation

pytestmark = pytest.mark.force_run


def test_normalize_zscore_and_index() -> None:
    points = [("d1", 1.0), ("d2", 2.0), ("d3", 3.0)]
    z = normalize_points(points, "zscore")
    assert abs(sum(p["norm"] for p in z)) < 1e-9
    idx = normalize_points(points, "index_100")
    assert idx[0]["norm"] == pytest.approx(100.0)
    assert idx[2]["norm"] == pytest.approx(300.0)


def test_pairwise_core_correlation_lead_and_scale() -> None:
    n = max(MIN_OVERLAP_REPORT, 12)
    # B_raw = 10 * A_raw → β(B|A) = 10；norm 同形
    payload = [
        {
            "id": "s0",
            "label": "A",
            "points": [
                {
                    "date": f"202001{i + 1:02d}",
                    "raw": float(i + 1),
                    "norm": float(i + 1),
                }
                for i in range(n)
            ],
        },
        {
            "id": "s1",
            "label": "B",
            "points": [
                {
                    "date": f"202001{i + 1:02d}",
                    "raw": 10.0 * float(i + 1),
                    "norm": float(i + 1),
                }
                for i in range(n)
            ],
        },
    ]
    rows = pairwise_summary(payload, max_lag=3)
    assert len(rows) == 1
    row = rows[0]
    assert row["overlap_n"] == n
    assert row["pearson"] == pytest.approx(1.0)
    assert row["relation"] == "positive"
    assert row["lead"] == "sync"
    assert row["beta_b_on_a"] == pytest.approx(10.0)
    assert row["alpha_b_on_a"] == pytest.approx(0.0)
    assert row["scale_r2"] == pytest.approx(1.0)
    assert row["shape_ok"] is True
    assert "一起" in row["core"]["relation_text"] or "方向一致" in row["core"]["relation_text"]
    assert "同步" in row["core"]["lead_text"]
    assert "10" in row["core"]["scale_text"]


def test_weak_shape_marks_lead_scale_untrusted() -> None:
    n = max(MIN_OVERLAP_REPORT, 12)
    # 近乎无关的两条线
    payload = [
        {
            "id": "s0",
            "label": "A",
            "points": [
                {"date": f"202001{i + 1:02d}", "raw": float(i), "norm": float(i)}
                for i in range(n)
            ],
        },
        {
            "id": "s1",
            "label": "B",
            "points": [
                {
                    "date": f"202001{i + 1:02d}",
                    "raw": float((i * 7) % 5),
                    "norm": float((i * 7) % 5),
                }
                for i in range(n)
            ],
        },
    ]
    row = pairwise_summary(payload)[0]
    if row["relation"] == "weak":
        assert row["shape_ok"] is False
        assert "谨慎" in row["core"]["lead_text"] or "不太像" in (
            row["warnings"][0] if row["warnings"] else ""
        )


def test_pairwise_insufficient_overlap() -> None:
    payload = [
        {
            "id": "s0",
            "points": [{"date": "20200101", "norm": 1.0}, {"date": "20200102", "norm": 2.0}],
        },
        {
            "id": "s1",
            "points": [{"date": "20200101", "norm": 1.0}, {"date": "20200102", "norm": 2.0}],
        },
    ]
    row = pairwise_summary(payload)[0]
    assert row["relation"] == "insufficient"
    assert row["reliable"] is False


def test_runner_writes_artifacts(tmp_path: Path) -> None:
    days = [f"202001{i + 1:02d}" for i in range(12)]

    def load_rows(data_key: str, *, entity_id: str = ""):
        if "lpr" in data_key:
            return [{"date": d, "lpr_1y": 4.0 + i * 0.01} for i, d in enumerate(days)]
        return [{"date": d, "close": 100.0 + i} for i, d in enumerate(days)]

    settings = {
        "meta": {"key": "demo"},
        "series": [
            {"data_key": "macro.lpr", "field": "lpr_1y", "label": "LPR", "scope": "global"},
            {
                "data_key": "stock.kline.daily",
                "entity_id": "000300.SH",
                "field": "close",
                "label": "IDX",
                "scope": "per_entity",
            },
        ],
        "range": {"start_date": "", "end_date": ""},
        "normalize": "none",
        "fill": "none",
        "analyze": True,
    }
    result = run_relation(settings, output_dir=tmp_path / "results", load_rows=load_rows)
    assert result["success"] is True
    findings = (tmp_path / "results" / "findings.md").read_text(encoding="utf-8")
    assert "同向还是反向" in findings
    assert "补充" in findings
    summary = json.loads((tmp_path / "results" / "summary.json").read_text())
    assert summary["pairwise"][0]["relation"] == "positive"
    assert summary["pairwise"][0]["beta_b_on_a"] is not None
    assert "scale_text" in summary["pairwise"][0]["core"]
    report = str(result.get("report") or "")
    assert "核心结论" in report
    assert "参与者" in report
    assert "同向还是反向:" in report
    assert (tmp_path / "results" / "report.txt").is_file()


def test_rolling_stability_answers_plainly() -> None:
    from core.modules.series_relation.core.pipeline.cli_report import (
        format_rolling_stability,
    )

    text = format_rolling_stability(
        {
            "window": 60,
            "mean": 0.40,
            "recent": 0.20,
            "sign_flips": 8,
            "n_windows": 667,
            "max_sign_flips": 666,
            "stability": "stable",
        }
    )
    assert "比较稳" in text
    assert "8/666" in text
    assert "翻转率" in text
    assert "平均≈0.40" in text  # 固定 2 位小数
