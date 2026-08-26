"""Step 2 — Analyze: read source → factor analysis pipeline → AnalyzeOutput."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.modules.strategy.core.services.artifacts import ArtifactIO

from ...support.paths import AnalyzerPaths
from .analyze_output import AnalyzeOutput
from .data import DecisionSpaceBuilder, StepOutcomeRegistry
from .pipeline import FactorAnalysisPipeline, StageInput


class AnalyzeStep:
    """Two steps: (1) read + prepare input (2) run factor-analysis pipeline."""

    @classmethod
    def run(
        cls,
        source_path: Union[str, Path],
        *,
        step: str,
        baseline_source: Optional[Dict[str, Any]] = None,
    ) -> AnalyzeOutput:
        source = ArtifactIO.read_json(Path(source_path))
        if not isinstance(source, dict):
            raise ValueError(f"invalid source.json: {source_path}")
        return cls.run_payload(
            source,
            step=step,
            baseline_source=baseline_source,
            source_path=Path(source_path),
        )

    @classmethod
    def run_payload(
        cls,
        source: Dict[str, Any],
        *,
        step: str,
        baseline_source: Optional[Dict[str, Any]] = None,
        source_path: Optional[Path] = None,
    ) -> AnalyzeOutput:
        capture_keys = list(
            (source.get("inputs") or {}).get("capture", {}).get("keys") or []
        )
        coverage = dict(
            (source.get("inputs") or {}).get("capture", {}).get("coverage") or {}
        )

        decision_space = DecisionSpaceBuilder.build(source)
        baseline_decision_space = (
            DecisionSpaceBuilder.build(baseline_source)
            if baseline_source
            else None
        )
        stage_input = StageInput(
            source=source,
            step=step,
            decision_space=decision_space,
            baseline_source=baseline_source,
            baseline_decision_space=baseline_decision_space,
        )
        attribution = FactorAnalysisPipeline.run(stage_input)

        resolved_path = source_path
        if resolved_path is None:
            out_dir = str(source.get("output_dir") or "").strip()
            resolved_path = (
                AnalyzerPaths.source_json(Path(out_dir))
                if out_dir
                else Path("analysis/source.json")
            )
        return AnalyzeOutput(
            source_path=Path(resolved_path),
            step=step,
            capture_keys=capture_keys,
            coverage=coverage,
            decision_space=decision_space,
            attribution=attribution,
            outcome_fields=cls._outcome_fields(step),
        )

    @staticmethod
    def _outcome_fields(step: str) -> List[str]:
        config = StepOutcomeRegistry.get(step)
        return [config.roi_field, config.result_field]
