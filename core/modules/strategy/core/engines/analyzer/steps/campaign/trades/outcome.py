"""层内 ROI / 胜负字段映射（战役内用，不依赖单 version analyze）。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet


@dataclass(frozen=True)
class StepOutcomeConfig:
    """一层单笔结果用的收益率和胜负字段。"""

    roi_field: str
    result_field: str = "engine.result"
    win_values: FrozenSet[str] = frozenset({"win"})


class StepOutcomeRegistry:
    """按层取出单笔结果字段。"""

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
        """返回该层的结果字段配置。"""
        key = str(step or "").strip().lower()
        if key not in cls._CONFIG:
            raise ValueError(f"不支持的归因层: {step!r}")
        return cls._CONFIG[key]
