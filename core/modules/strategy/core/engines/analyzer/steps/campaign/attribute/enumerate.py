"""枚举层战役归因：找机会 + 纸面目标，不含资金/仓位旋钮。"""
from __future__ import annotations

from .base import AttributeBase


class EnumerateAttributeStep(AttributeBase):
    """sea：只问机会与 goal 纸面结局，对应 settings 的 core/goal/data/sampling。"""

    LAYER = "enum"
    KNOB_PREFIXES = ("core.", "goal.", "data.", "sampling.")
    OUTCOMES = (
        ("enum", "total_opportunities"),
        ("enum", "trigger_ratio"),
        ("enum", "top_bucket_ratio"),
        ("enum", "cv"),
        ("enum", "stop_loss_ratio"),
        ("enum", "take_profit_ratio"),
    )
