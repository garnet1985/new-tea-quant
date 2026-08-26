"""Strategy attribution analyzer — API 暴露层。"""
from __future__ import annotations

from typing import Any, Dict, Optional, Union

from core.modules.strategy.core.services.artifacts import ArtifactStore

from .io.step_payload import StepAnalysisPayload
from .pipeline import AnalyzerAutoRun, AnalyzerPipeline
from .steps import AnalyzeStep, PrepareStep, ReportStep
from .steps.report import (
    AnalysisReportPresenter,
    InsightBuilder,
    ReportNarrative,
)
from .support.output_dirs import SimulationOutputDirs
from .support.paths import AnalyzerPaths
from .support.step_mapping import AnalyzerStepMapping


class Analyzer:
    """Workbench attribution: Prepare → Analyze → Report."""

    Pipeline = AnalyzerPipeline
    AutoRun = AnalyzerAutoRun
    Prepare = PrepareStep
    Analyze = AnalyzeStep
    Report = ReportStep
    Insights = InsightBuilder
    Narrative = ReportNarrative
    Presenter = AnalysisReportPresenter
    Paths = AnalyzerPaths
    OutputDirs = SimulationOutputDirs
    Step = AnalyzerStepMapping
    Payload = StepAnalysisPayload

    @classmethod
    def run(
        cls,
        store: ArtifactStore,
        *,
        baseline_version_id: Optional[str] = None,
        strategy_folder: Optional[Union[str, Any]] = None,
    ) -> Dict[str, Any]:
        return AnalyzerPipeline.run(
            store,
            baseline_version_id=baseline_version_id,
            strategy_folder=strategy_folder,
        )
