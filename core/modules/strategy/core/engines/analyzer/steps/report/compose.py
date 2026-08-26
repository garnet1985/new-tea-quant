"""Reorganize analyze output into ``report.json`` payload."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Union

from ...support.paths import AnalyzerPaths
from ..analyze.analyze_output import AnalyzeOutput
from ._insights import InsightBuilder
from .narrative import ReportNarrative
from .skip_summary import PriceSkipSummary


class ReportComposer:
    """Merge ``AnalyzeOutput`` + source metadata into a report document."""

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
