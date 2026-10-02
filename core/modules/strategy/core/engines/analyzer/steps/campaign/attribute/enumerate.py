"""枚举层战役归因：找机会 + 纸面目标，不含资金/仓位旋钮。"""
from __future__ import annotations

from .base import AttributeBase


class EnumerateAttributeStep(AttributeBase):
    """sea：只问机会与 goal 纸面结局，对应 settings 的 core/goal/data/sampling。"""

    LAYER = "enumerate"
    KNOB_PREFIXES = ("core.", "goal.", "data.", "sampling.")
    OUTCOMES = (
        ("enumerate", "total_opportunities"),
    )
    ENABLE_INTERACTIONS = False
    ENABLE_CROSS_LAYER = False
