"""组合层战役总结（soa）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import SummarizeBase


class PortfolioSummarize(SummarizeBase):
    LAYER = "portfolio"
    KIND = SimulateKind.PORTFOLIO
