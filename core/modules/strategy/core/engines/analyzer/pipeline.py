"""Analyzer 编排：collect → 写 analysis/source.json + report.json。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.io import ArtifactIO

from .collector import AttributionInputCollector
from .consts import ANALYSIS_SUBDIR, REPORT_JSON, SOURCE_JSON
from .report import AttributionReportBuilder
from .step import step_value


class AnalyzerPipeline:
    """归因 input 收集 + 决定空间 report。"""

    @classmethod
    def run(cls, store: ArtifactStore) -> Dict[str, Any]:
        store._ensure_runtime()
        source = AttributionInputCollector(store).collect()
        source["collected_at"] = datetime.now().isoformat()
        analysis_dir = Path(store.output_dir) / ANALYSIS_SUBDIR
        source_path = analysis_dir / SOURCE_JSON
        ArtifactIO.write_json(source_path, source)

        report = AttributionReportBuilder.build(
            source,
            step=step_value(store.kind),
        )
        report_path = analysis_dir / REPORT_JSON
        ArtifactIO.write_json(report_path, report)

        entity_count = len(source.get("entities") or [])
        investment_count = int(
            (source.get("inputs") or {})
            .get("capture", {})
            .get("coverage", {})
            .get("investment_count", 0)
        )
        return {
            "success": True,
            "step": step_value(store.kind),
            "version_id": str(store.version_id),
            "output_dir": str(store.output_dir.resolve()),
            "analysis_dir": str(analysis_dir.resolve()),
            "source_path": str(source_path.resolve()),
            "report_path": str(report_path.resolve()),
            "entity_count": entity_count,
            "investment_count": investment_count,
        }


__all__ = ["AnalyzerPipeline"]
