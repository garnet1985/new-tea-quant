"""价格层战役计划（spa）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import AttributionPlanBase


class PriceAttributionPlan(AttributionPlanBase):
    LAYER = "price_factor"
    KIND = SimulateKind.PRICE_FACTOR
