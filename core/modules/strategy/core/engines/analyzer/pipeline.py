"""Analyzer 编排：collect → 写 analysis/source.json + report.json。"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.io import ArtifactIO

from .collector import AttributionInputCollector
from .consts import ANALYSIS_SUBDIR, REPORT_JSON, SOURCE_JSON
from .baseline_source import load_baseline_source
from .report import AttributionReportBuilder
from .step import step_value


class AnalyzerPipeline:
    """归因 input 收集 + 决定空间 report。"""

    @classmethod
    def run(
        cls,
        store: ArtifactStore,
        *,
        baseline_version_id: Optional[str] = None,
        strategy_folder: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        store._ensure_runtime()
        source = AttributionInputCollector(store).collect()
        source["collected_at"] = datetime.now().isoformat()
        analysis_dir = Path(store.output_dir) / ANALYSIS_SUBDIR
        source_path = analysis_dir / SOURCE_JSON
        ArtifactIO.write_json(source_path, source)

        baseline_source = None
        baseline_vid = str(baseline_version_id or "").strip()
        if baseline_vid:
            if strategy_folder is None:
                raise ValueError(
                    "run_comparison 需要 strategy_folder 以加载 baseline version"
                )
            baseline_source = load_baseline_source(
                strategy_folder,
                kind=store.kind,
                baseline_version_id=baseline_vid,
            )

        report = AttributionReportBuilder.build(
            source,
            step=step_value(store.kind),
            baseline_source=baseline_source,
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
