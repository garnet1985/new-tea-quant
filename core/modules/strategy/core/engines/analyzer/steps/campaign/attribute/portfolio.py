"""组合层战役归因：资金与仓位结局；参数不按前缀收窄。"""
from __future__ import annotations

from .base import AttributeBase


class PortfolioAttributeStep(AttributeBase):
    """soa：问账户收益/回撤；portfolio 等下游参数在此才进。"""

    LAYER = "portfolio"
    KNOB_PREFIXES = ()
    OUTCOMES = (
        ("portfolio", "total_return"),
        ("portfolio", "max_drawdown"),
        ("enum", "total_opportunities"),
        ("price", "win_rate"),
        ("price", "avg_roi"),
    )
