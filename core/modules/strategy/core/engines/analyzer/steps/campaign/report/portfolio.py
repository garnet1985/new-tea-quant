"""组合层战役报告（soa）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import ReportBase


class PortfolioReport(ReportBase):
    LAYER = "portfolio"
    KIND = SimulateKind.PORTFOLIO
