"""Run comparison — current vs baseline, delegate diff to ``modules.analysis``."""
from __future__ import annotations

from typing import Any, Dict

from core.modules.analysis import Analysis

from ..context import StageInput


class RunComparisonStage:
    name = "run_comparison"

    def run(self, stage_input: StageInput) -> Dict[str, Any]:
        if (
            stage_input.baseline_source is None
            or stage_input.baseline_decision_space is None
        ):
            return {"status": "not_requested"}

        current_summary = self._run_summary(
            stage_input.source,
            stage_input.decision_space,
        )
        baseline_summary = self._run_summary(
            stage_input.baseline_source,
            stage_input.baseline_decision_space,
        )
        comparison = Analysis.Classical.compare_run_summaries(
            current_summary,
            baseline_summary,
        )
        return {
            "status": comparison.get("status", "skipped"),
            "baseline_version_id": baseline_summary.get("version_id"),
            "comparison": comparison,
        }

    @staticmethod
    def _run_summary(
        source: Dict[str, Any],
        decision_space: Dict[str, Any],
    ) -> Dict[str, Any]:
        inputs = source.get("inputs") or {}
        capture = (
            inputs.get("capture") if isinstance(inputs.get("capture"), dict) else {}
        )
        return {
            "version_id": source.get("version_id"),
            "decision_space": decision_space,
            "coverage": dict(capture.get("coverage") or {}),
        }


__all__ = ["RunComparisonStage"]
