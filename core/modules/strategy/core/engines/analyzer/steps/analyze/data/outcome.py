"""Per-step outcome field mapping for factor analysis stages."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet


@dataclass(frozen=True)
class StepOutcomeConfig:
    roi_field: str
    result_field: str = "engine.result"
    win_values: FrozenSet[str] = frozenset({"win"})


class StepOutcomeRegistry:
    _CONFIG: Dict[str, StepOutcomeConfig] = {
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

    @classmethod
    def get(cls, step: str) -> StepOutcomeConfig:
        key = str(step or "").strip().lower()
        if key not in cls._CONFIG:
            raise ValueError(f"unsupported attribution step: {step!r}")
        return cls._CONFIG[key]
