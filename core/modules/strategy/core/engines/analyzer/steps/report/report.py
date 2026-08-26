"""Step 3 — 组装 report（叙事 + insights）并落盘 ``analysis/report.json``。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Union

from core.modules.strategy.core.services.artifacts import ArtifactStore

from ...support.paths import AnalyzerPaths
from ..analyze.analyze_output import AnalyzeOutput
from .insights import InsightBuilder
from .report_narrative import ReportNarrative
from .report_output import ReportOutput
from .report_writer import ReportWriter
from .skip_summary import PriceSkipSummary


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
        report_path = ReportWriter.write(store, report)
        return ReportOutput.from_payload(report_path=report_path, report=report)

    @classmethod
    def build(
        cls,
        source: Dict[str, Any],
        *,
        analyze_out: Union[AnalyzeOutput, Dict[str, Any]],
    ) -> Dict[str, Any]:
        analyze_result = (
            analyze_out.to_dict()
            if isinstance(analyze_out, AnalyzeOutput)
            else dict(analyze_out)
        )
        step = (
            analyze_out.step
            if isinstance(analyze_out, AnalyzeOutput)
            else str(analyze_result.get("step") or source.get("step") or "enum")
        )
        decision_space = dict(analyze_result.get("decision_space") or {})
        attribution = dict(analyze_result.get("attribution") or {})
        classical = dict(attribution.get("classical") or {})
        classical["scope_note"] = ReportNarrative.scope_note(step)
        if step == "price":
            classical["skip_summary"] = PriceSkipSummary.build(source)
        attribution = {**attribution, "classical": classical}
        hints_for_ui = ReportNarrative.hints_for_ui(
            step=step,
            decision_space=decision_space,
            attribution=attribution,
        )
        report = {
            "schema_version": AnalyzerPaths.SCHEMA_VERSION,
            "step": step,
            "version_id": str(source.get("version_id") or ""),
            "strategy_key": str(source.get("strategy_key") or ""),
            "generated_at": datetime.now().isoformat(),
            "manifest": {
                "capture_keys": list(analyze_result.get("capture_keys") or []),
                "coverage": dict(analyze_result.get("coverage") or {}),
                "outcome_fields": list(analyze_result.get("outcome_fields") or []),
            },
            "decision_space": decision_space,
            "attribution": attribution,
            "hints_for_ui": hints_for_ui,
        }
        report["insights"] = InsightBuilder.build(report)
        return report
