"""价格层战役收集（spa）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import GatherBase


class PriceGather(GatherBase):
    LAYER = "price_factor"
    KIND = SimulateKind.PRICE_FACTOR
