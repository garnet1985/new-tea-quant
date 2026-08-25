"""Per-step outcome field mapping for attribution stages."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Tuple


@dataclass(frozen=True)
class StepOutcomeConfig:
    """Dotted paths under each investment row in ``source.json``."""

    roi_field: str
    result_field: str = "engine.result"
    win_values: FrozenSet[str] = frozenset({"win"})


STEP_OUTCOME_CONFIG: Dict[str, StepOutcomeConfig] = {
    "enum": StepOutcomeConfig(
        roi_field="engine.weighted_roi",
        result_field="engine.result",
        win_values=frozenset({"win"}),
    ),
    "price": StepOutcomeConfig(
        roi_field="engine.roi",
        result_field="engine.result",
        win_values=frozenset({"win"}),
    ),
    "portfolio": StepOutcomeConfig(
        roi_field="engine.roi",
        result_field="engine.result",
        win_values=frozenset({"win"}),
    ),
}


def get_step_outcome_config(step: str) -> StepOutcomeConfig:
    key = str(step or "").strip().lower()
    if key not in STEP_OUTCOME_CONFIG:
        raise ValueError(f"unsupported attribution step: {step!r}")
    return STEP_OUTCOME_CONFIG[key]


__all__ = ["STEP_OUTCOME_CONFIG", "StepOutcomeConfig", "get_step_outcome_config"]
