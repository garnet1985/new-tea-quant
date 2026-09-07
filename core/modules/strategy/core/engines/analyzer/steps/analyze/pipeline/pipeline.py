"""Iterate factor-analysis stages; collect results for Report."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .context import AnalysisStage, StageInput
from .stages import DEFAULT_STAGES


class FactorAnalysisPipeline:
    """Run each analysis stage with shared ``StageInput``; merge outputs."""

    @classmethod
    def run(
        cls,
        stage_input: StageInput,
        *,
        stages: Optional[Iterable[AnalysisStage]] = None,
    ) -> Dict[str, Any]:
        classical: Dict[str, Any] = {}
        ml: Dict[str, Any] = {"status": "skipped", "reason": "not_run"}
        for stage in stages or DEFAULT_STAGES:
            fragment = stage.run(stage_input)
            if stage.name == "ml":
                ml = fragment
            else:
                classical[stage.name] = fragment

        classical_status = cls._classical_status(classical)
        return {
            "classical": {
                "status": classical_status,
                **classical,
            },
            "ml": ml,
        }

    @staticmethod
    def _classical_status(classical: Dict[str, Any]) -> str:
        if not classical:
            return "skipped"
        univariate = classical.get("univariate") or {}
        if univariate.get("status") == "skipped" and len(univariate.get("fields") or {}) == 0:
            return "skipped"
        statuses = [
            part.get("status")
            for part in classical.values()
            if isinstance(part, dict) and "status" in part
        ]
        if any(status == "stub" for status in statuses):
            return "stub"
        if any(status == "partial" for status in statuses):
            return "partial"
        if any(status in ("ok", "not_requested") for status in statuses):
            return "ok"
        return "skipped"


__all__ = ["FactorAnalysisPipeline"]
