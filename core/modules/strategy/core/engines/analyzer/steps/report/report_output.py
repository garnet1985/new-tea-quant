"""Report step deliverable."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class ReportOutput:
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
