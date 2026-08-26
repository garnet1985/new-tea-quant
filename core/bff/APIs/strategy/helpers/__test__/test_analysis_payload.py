"""Tests for BFF analysis insights loader."""

from __future__ import annotations

import json
from pathlib import Path

from core.bff.APIs.strategy.helpers.analysis_payload import (
    load_step_analysis,
    resolve_analysis_for_step,
)


def test_load_step_analysis_missing(tmp_path: Path) -> None:
    payload = load_step_analysis(tmp_path)
    assert payload["available"] is False
    assert payload["insights"] is None


def test_load_step_analysis_reads_insights(tmp_path: Path) -> None:
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()
    (analysis_dir / "report.json").write_text(
        json.dumps(
            {
                "step": "enum",
                "insights": {
                    "status": "ok",
                    "headline": "测试结论",
                    "key_findings": [],
                },
            }
        ),
        encoding="utf-8",
    )
    payload = load_step_analysis(tmp_path)
    assert payload["available"] is True
    assert payload["insights"]["headline"] == "测试结论"


def test_resolve_analysis_for_step_uses_output_dir(monkeypatch, tmp_path: Path) -> None:
    analysis_dir = tmp_path / "analysis"
    analysis_dir.mkdir()
    (analysis_dir / "report.json").write_text(
        json.dumps({"insights": {"headline": "from disk"}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "core.bff.APIs.strategy.helpers.report_hydrate.resolve_simulation_output_dirs",
        lambda *a, **k: [tmp_path],
    )
    payload = resolve_analysis_for_step(
        "demo/x",
        "enum",
        {"output_dir": str(tmp_path)},
        workbench_version=2,
    )
    assert payload["available"] is True
    assert payload["insights"]["headline"] == "from disk"
