"""价格层战役执行（spa）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import ExecuteBase


class PriceExecute(ExecuteBase):
    LAYER = "price_factor"
    KIND = SimulateKind.PRICE_FACTOR
