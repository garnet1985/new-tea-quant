"""组合层战役计划（soa）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import AttributionPlanBase


class PortfolioAttributionPlan(AttributionPlanBase):
    LAYER = "portfolio"
    KIND = SimulateKind.PORTFOLIO
