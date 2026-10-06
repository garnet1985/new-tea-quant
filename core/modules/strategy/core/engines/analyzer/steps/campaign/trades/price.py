"""价格层单笔铺平（spa）：XGB + SHAP。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import TradesBase


class PriceTrades(TradesBase):
    LAYER = "price_factor"
    KIND = SimulateKind.PRICE_FACTOR
