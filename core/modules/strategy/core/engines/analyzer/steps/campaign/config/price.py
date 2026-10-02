"""价格层战役配置（spa）。"""
from __future__ import annotations

from core.modules.strategy.core.enums import SimulateKind

from .base import AttributionConfigBase


class PriceAttributionConfig(AttributionConfigBase):
    """spa：去噪账对照；声明与枚举相同，执行/收集不同。"""

    LAYER = "price_factor"
    KIND = SimulateKind.PRICE_FACTOR
