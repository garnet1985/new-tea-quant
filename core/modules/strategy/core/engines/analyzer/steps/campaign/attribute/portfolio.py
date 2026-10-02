"""组合层战役归因：资金与仓位结局；旋钮不按前缀收窄。"""
from __future__ import annotations

from .base import AttributeBase


class PortfolioAttributeStep(AttributeBase):
    """soa：问账户收益/回撤；portfolio 等下游旋钮在此才进。"""

    LAYER = "portfolio"
    KNOB_PREFIXES = ()  # 空 = 不按前缀限制
    OUTCOMES = (
        ("portfolio", "total_return"),
        ("portfolio", "max_drawdown"),
        ("enumerate", "total_opportunities"),
        ("price_factor", "win_rate"),
        ("price_factor", "avg_roi"),
    )
    ENABLE_INTERACTIONS = True
    ENABLE_CROSS_LAYER = True
