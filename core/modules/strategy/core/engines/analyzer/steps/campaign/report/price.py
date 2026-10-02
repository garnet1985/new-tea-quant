"""价格层战役报告（spa）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import ReportBase


class PriceReport(ReportBase):
    LAYER = "price_factor"
    KIND = SimulateKind.PRICE_FACTOR
