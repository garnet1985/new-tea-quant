"""Step 3 — Report: 总结 → insight → 持久化（展示见 present.py）。"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Union

from core.modules.strategy.core.services.artifacts import ArtifactStore

from ..analyze.analyze_output import AnalyzeOutput
from .insight import InsightBuilder
from .summarize import ReportSummarizer

_EMPTY_PAYLOAD: Dict[str, Any] = {
    "available": False,
    "report_path": "",
    "insights": None,
}


@dataclass(frozen=True)
class ReportOutput:
    """Report 步产出 — 磁盘上的 ``analysis/report.json``。"""

    report_path: Path
    analysis_dir: Path
    step: str
    version_id: str

    @classmethod
    def from_payload(
        cls,
        *,
        report_path: Path,
        report: Dict[str, Any],
    ) -> "ReportOutput":
        return cls(
            report_path=Path(report_path),
            analysis_dir=Path(report_path).parent,
            step=str(report.get("step") or ""),
            version_id=str(report.get("version_id") or ""),
        )


class ReportStep:
    @classmethod
    def run(
        cls,
        store: ArtifactStore,
        source: Dict[str, Any],
        *,
        analyze_out: Union[AnalyzeOutput, Dict[str, Any]],
    ) -> ReportOutput:
        report = cls.build(source, analyze_out=analyze_out)
        report_path = store.write_json("analysis_report", report)
        return ReportOutput.from_payload(report_path=report_path, report=report)

    @classmethod
    def build(
        cls,
        source: Dict[str, Any],
        *,
        analyze_out: Union[AnalyzeOutput, Dict[str, Any]],
    ) -> Dict[str, Any]:
        report = ReportSummarizer.build(source, analyze_out=analyze_out)
        report["insights"] = InsightBuilder.build(report)
        return report

    @classmethod
    def load_payload(cls, output_dir: Union[str, Path]) -> Dict[str, Any]:
        """Read ``analysis/report.json`` insights payload for BFF / UI."""
        path = Path(output_dir)
        report_path = ArtifactStore.named_path(path, "analysis_report")
        if not report_path.is_file():
            return dict(_EMPTY_PAYLOAD)
        try:
            report = ArtifactStore.read_json_at(path, "analysis_report")
        except Exception:
            return dict(_EMPTY_PAYLOAD)
        if not isinstance(report, dict):
            return dict(_EMPTY_PAYLOAD)

        insights = InsightBuilder.resolve(report)

        return {
            "available": True,
            "report_path": str(report_path),
            "insights": insights,
        }
