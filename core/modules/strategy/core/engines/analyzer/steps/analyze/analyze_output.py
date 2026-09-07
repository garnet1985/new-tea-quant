"""Analyze step deliverable."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass(frozen=True)
class AnalyzeOutput:
    source_path: Path
    step: str
    capture_keys: List[str]
    coverage: Dict[str, Any]
    decision_space: Dict[str, Any]
    attribution: Dict[str, Any]
    outcome_fields: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "capture_keys": list(self.capture_keys),
            "coverage": dict(self.coverage),
            "decision_space": dict(self.decision_space),
            "attribution": dict(self.attribution),
            "outcome_fields": list(self.outcome_fields),
        }
