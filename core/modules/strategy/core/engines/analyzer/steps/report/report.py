"""Step 3 — Report: compose analyze results → persist → present."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Union

from core.modules.strategy.core.services.artifacts import ArtifactStore

from ..analyze.analyze_output import AnalyzeOutput
from .compose import ReportComposer


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
    """Three phases: input from analyze → compose + persist → (optional) present."""

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
        return ReportComposer.build(source, analyze_out=analyze_out)

    @classmethod
    def read(cls, store: ArtifactStore) -> Dict[str, Any]:
        return store.read_json("analysis_report")
