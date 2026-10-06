"""价格层战役落盘（spa）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import PersistBase


class PricePersist(PersistBase):
    LAYER = "price_factor"
    KIND = SimulateKind.PRICE_FACTOR
    TASK_ID = "price_factor"
