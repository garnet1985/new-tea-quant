"""Strategy attribution analyzer — Facade。

归因入口按层：``attribute_enumerate`` / ``attribute_price`` / ``attribute_portfolio``。
回测不再自动归因；单号切片 ``run`` 仅供战役内部（如价格层 trades）使用。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from core.modules.strategy.core.enums import SimulateKind, WorkbenchStep
from core.modules.strategy.core.services.artifacts import ArtifactStore
from core.modules.strategy.core.services.artifacts.consts import ANALYSIS_SUBDIR

from .consts import report_ready
from .pipeline import AttributionPipeline, RollingPipeline
from .steps import AnalyzeStep, PrepareStep, ReportStep
from .steps.campaign.present import CampaignPresenter
from .steps.report import AnalysisReportPresenter
from .steps.rolling.present import RollingPresenter


class Analyzer:
    Prepare = PrepareStep
    Analyze = AnalyzeStep
    Report = ReportStep
    Presenter = AnalysisReportPresenter
    Campaign = AttributionPipeline
    Rolling = RollingPipeline
    CampaignPresenter = CampaignPresenter
    RollingPresenter = RollingPresenter

    @classmethod
    def run(
        cls,
        store: ArtifactStore,
        *,
        baseline_version_id: Optional[str] = None,
        strategy_folder: Optional[Union[str, Path]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Prepare → Analyze → Report（战役内部切片，不对外 CLI）。"""
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
    def attribute(
        cls,
        key_or_id: Union[str, Path],
        *,
        kind: Union[SimulateKind, str],
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """读 attribution.py，按层对照旋钮，写出战役总结。"""
        return AttributionPipeline.run(
            key_or_id, kind=kind, ignore_cache=ignore_cache
        )

    @classmethod
    def attribute_enumerate(
        cls,
        key_or_id: Union[str, Path],
        *,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        return cls.attribute(
            key_or_id, kind=SimulateKind.ENUMERATE, ignore_cache=ignore_cache
        )

    @classmethod
    def attribute_price(
        cls,
        key_or_id: Union[str, Path],
        *,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        return cls.attribute(
            key_or_id, kind=SimulateKind.PRICE_FACTOR, ignore_cache=ignore_cache
        )

    @classmethod
    def attribute_portfolio(
        cls,
        key_or_id: Union[str, Path],
        *,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        return cls.attribute(
            key_or_id, kind=SimulateKind.PORTFOLIO, ignore_cache=ignore_cache
        )

    @classmethod
    def rolling(
        cls,
        key_or_id: Union[str, Path],
        *,
        ignore_cache: bool = False,
    ) -> Dict[str, Any]:
        """读 attribution.py 的 rolling 窗口，写出滚动总结。"""
        return RollingPipeline.run(key_or_id, ignore_cache=ignore_cache)
