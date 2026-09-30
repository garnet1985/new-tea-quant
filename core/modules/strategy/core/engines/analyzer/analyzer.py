"""Strategy attribution analyzer — Facade（战役库入口；simulate 不再自动调用）。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from core.modules.strategy.core.enums import WorkbenchStep
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.consts import ANALYSIS_SUBDIR

from .consts import report_ready
from .pipeline import AttributionPipeline
from .steps import AnalyzeStep, PrepareStep, ReportStep
from .steps.campaign.present import CampaignPresenter
from .steps.report import AnalysisReportPresenter


class Analyzer:
    Prepare = PrepareStep
    Analyze = AnalyzeStep
    Report = ReportStep
    Presenter = AnalysisReportPresenter
    Campaign = AttributionPipeline
    CampaignPresenter = CampaignPresenter

    @classmethod
    def run(
        cls,
        store: ArtifactStore,
        *,
        baseline_version_id: Optional[str] = None,
        strategy_folder: Optional[Union[str, Path]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Prepare → Analyze → Report。"""
        if not force and report_ready(store.output_dir):
            report_path = store.file("analysis_report")
            return {
                "success": True,
                "skipped": True,
                "reason": "exists",
                "report_path": str(report_path.resolve()),
                "output_dir": str(store.output_dir.resolve()),
            }

        store._ensure_runtime()

        prepare_out = PrepareStep.run(store)
        source = store.read_json("analysis_source")

        baseline_source = None
        baseline_vid = str(baseline_version_id or "").strip()
        if baseline_vid:
            if strategy_folder is None:
                raise ValueError(
                    "run_comparison 需要 strategy_folder 以加载 baseline version"
                )
            from .steps.analyze import BaselineSourceLoader

            baseline_source = BaselineSourceLoader.load(
                strategy_folder,
                kind=store.kind,
                baseline_version_id=baseline_vid,
            )

        workbench_step = WorkbenchStep.from_simulate_kind(store.kind)
        if workbench_step is None:
            raise ValueError(f"unsupported simulation step: {store.kind!r}")
        step = workbench_step.value

        analyze_out = AnalyzeStep.run(
            prepare_out.source_path,
            step=step,
            baseline_source=baseline_source,
        )
        report_out = ReportStep.run(store, source, analyze_out=analyze_out)

        analysis_dir = Path(store.output_dir) / ANALYSIS_SUBDIR
        return {
            "success": True,
            "skipped": False,
            "step": step,
            "version_id": str(store.version_id),
            "output_dir": str(store.output_dir.resolve()),
            "analysis_dir": str(analysis_dir.resolve()),
            "source_path": str(prepare_out.source_path.resolve()),
            "report_path": str(report_out.report_path.resolve()),
            "entity_count": prepare_out.entity_count,
            "investment_count": prepare_out.investment_count,
        }

    @classmethod
    def campaign(
        cls,
        key_or_id: Union[str, Path],
        *,
        fill_missing: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """读 attribution.py，对照各格旋钮，写出战役总结。

        ``fill_missing`` 非空时覆盖 attribution.py（CLI ``-f`` 用来补跑缺失格子）。
        """
        return AttributionPipeline.run(key_or_id, fill_missing=fill_missing)
