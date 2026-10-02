"""价格层战役总结（spa）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import SummarizeBase


class PriceSummarize(SummarizeBase):
    LAYER = "price_factor"
    KIND = SimulateKind.PRICE_FACTOR
