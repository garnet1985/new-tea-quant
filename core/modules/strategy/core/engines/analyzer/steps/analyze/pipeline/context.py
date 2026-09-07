"""Shared input for one factor-analysis stage run."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol


@dataclass
class StageInput:
    """Strategy-prepared input bundle passed to each analysis stage."""

    source: Dict[str, Any]
    step: str
    decision_space: Dict[str, Any]
    baseline_source: Optional[Dict[str, Any]] = None
    baseline_decision_space: Optional[Dict[str, Any]] = None
    options: Dict[str, Any] = field(default_factory=dict)


class AnalysisStage(Protocol):
    """One factor-analysis member in the pipeline."""

    name: str

    def run(self, stage_input: StageInput) -> Dict[str, Any]:
        """Return a fragment merged into ``AnalyzeOutput.attribution``."""


__all__ = ["AnalysisStage", "StageInput"]
