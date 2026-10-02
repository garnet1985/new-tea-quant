"""价格层战役归因：去噪账，仍不含组合资金旋钮。"""
from __future__ import annotations

from .base import AttributeBase


class PriceAttributeStep(AttributeBase):
    """spa：问去噪 ROI / 胜率；可动 simulation，不动 portfolio。"""

    LAYER = "price_factor"
    KNOB_PREFIXES = ("core.", "goal.", "data.", "sampling.", "simulation.")
    OUTCOMES = (
        ("price_factor", "avg_roi"),
        ("price_factor", "win_rate"),
        ("enumerate", "total_opportunities"),
    )
    ENABLE_INTERACTIONS = True
    ENABLE_CROSS_LAYER = True
