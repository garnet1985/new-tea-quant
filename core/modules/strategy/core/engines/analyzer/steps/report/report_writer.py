"""Write ``analysis/report.json``."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.io import ArtifactIO

from ...support.paths import AnalyzerPaths


class ReportWriter:
    @classmethod
    def write(cls, store: ArtifactStore, report: Dict[str, Any]) -> Path:
        analysis_dir = Path(store.output_dir) / AnalyzerPaths.ANALYSIS_SUBDIR
        analysis_dir.mkdir(parents=True, exist_ok=True)
        report_path = analysis_dir / AnalyzerPaths.REPORT_JSON
        ArtifactIO.write_json(report_path, report)
        return report_path
