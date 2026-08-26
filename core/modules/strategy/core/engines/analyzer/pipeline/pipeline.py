"""3-step analyzer orchestration."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from core.modules.strategy.core.services.artifacts import ArtifactStore

from ..steps.analyze import AnalyzeStep, BaselineSourceLoader
from ..steps.prepare import PrepareStep, SourceWriter
from ..steps.report import ReportStep
from ..support.paths import AnalyzerPaths
from ..support.step_mapping import AnalyzerStepMapping


class AnalyzerPipeline:
    """Prepare → analyze → report."""

    @classmethod
    def run(
        cls,
        store: ArtifactStore,
        *,
        baseline_version_id: Optional[str] = None,
        strategy_folder: Optional[Union[str, Path]] = None,
    ) -> Dict[str, Any]:
        store._ensure_runtime()

        prepare_out = PrepareStep.run(store)
        source = SourceWriter.read(prepare_out.source_path)

        baseline_source = None
        baseline_vid = str(baseline_version_id or "").strip()
        if baseline_vid:
            if strategy_folder is None:
                raise ValueError(
                    "run_comparison 需要 strategy_folder 以加载 baseline version"
                )
            baseline_source = BaselineSourceLoader.load(
                strategy_folder,
                kind=store.kind,
                baseline_version_id=baseline_vid,
            )

        step = AnalyzerStepMapping.value(store.kind)
        analyze_out = AnalyzeStep.run(
            prepare_out.source_path,
            step=step,
            baseline_source=baseline_source,
        )
        report_out = ReportStep.run(store, source, analyze_out=analyze_out)

        analysis_dir = Path(store.output_dir) / AnalyzerPaths.ANALYSIS_SUBDIR
        return {
            "success": True,
            "step": step,
            "version_id": str(store.version_id),
            "output_dir": str(store.output_dir.resolve()),
            "analysis_dir": str(analysis_dir.resolve()),
            "source_path": str(prepare_out.source_path.resolve()),
            "report_path": str(report_out.report_path.resolve()),
            "entity_count": prepare_out.entity_count,
            "investment_count": prepare_out.investment_count,
        }
