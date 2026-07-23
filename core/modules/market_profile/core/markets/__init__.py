#!/usr/bin/env python3
"""所有市场规则注册表。"""

from typing import Dict, Type

from ..base.market_base_rules import MarketBaseRules
from .china_a_stock import ChinaAStockRules
from .hong_kong import HongKongRules
from .us_stock import USStockRules
from .commodity_future import CommodityFutureRules
from .forex import ForexRules
from .crypto import CryptoRules

# 注册所有市场规则
MARKET_RULES_REGISTRY: Dict[str, Type[MarketBaseRules]] = {
    "china_a_stock": ChinaAStockRules,
    "hong_kong": HongKongRules,
    "us_stock": USStockRules,
    "commodity_future": CommodityFutureRules,
    "forex": ForexRules,
    "crypto": CryptoRules,
}


def get_available_markets() -> list[str]:
    """获取所有可用市场ID"""
    return list(MARKET_RULES_REGISTRY.keys())


def create_market_rules(profile_id: str) -> MarketBaseRules:
    """创建市场规则实例"""
    if profile_id not in MARKET_RULES_REGISTRY:
        raise ValueError(f"Unknown market profile: {profile_id}")

    return MARKET_RULES_REGISTRY[profile_id]()


__all__ = [
    "MARKET_RULES_REGISTRY",
    "get_available_markets",
    "create_market_rules",
    "ChinaAStockRules",
    "HongKongRules",
    "USStockRules",
    "CommodityFutureRules",
    "ForexRules",
    "CryptoRules",
]