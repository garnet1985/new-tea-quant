"""组合层战役配置（soa）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import AttributionConfigBase


class PortfolioAttributionConfig(AttributionConfigBase):
    """soa：资金与仓位对照；下游参数在此层才有意义。"""

    LAYER = "portfolio"
    KIND = SimulateKind.PORTFOLIO
