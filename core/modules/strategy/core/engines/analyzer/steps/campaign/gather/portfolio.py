"""组合层战役收集（soa）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import GatherBase


class PortfolioGather(GatherBase):
    LAYER = "portfolio"
    KIND = SimulateKind.PORTFOLIO
