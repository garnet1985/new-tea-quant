#!/usr/bin/env python3
"""内置市场规则注册表（模块内部；跨模块请用 ``MarketRulesProxy.for_market``）。"""

from typing import Dict, Type

from ..base.market_base_rules import MarketBaseRules
from .china_a_stock import ChinaAStockRules
from .hong_kong import HongKongRules
from .us_stock import USStockRules
from .commodity_future import CommodityFutureRules
from .forex import ForexRules
from .crypto import CryptoRules

MARKET_RULES_REGISTRY: Dict[str, Type[MarketBaseRules]] = {
    "china_a_stock": ChinaAStockRules,
    "hong_kong": HongKongRules,
    "us_stock": USStockRules,
    "commodity_future": CommodityFutureRules,
    "forex": ForexRules,
    "crypto": CryptoRules,
}


def get_available_markets() -> list[str]:
    """获取所有可用市场 ID（内部）。"""
    return list(MARKET_RULES_REGISTRY.keys())


def create_market_rules(profile_id: str) -> MarketBaseRules:
    """创建市场规则实例（内部；对外用 ``MarketRulesProxy.for_market``）。"""
    if profile_id not in MARKET_RULES_REGISTRY:
        raise ValueError(f"Unknown market profile: {profile_id}")

    return MARKET_RULES_REGISTRY[profile_id]()


__all__ = [
    "MARKET_RULES_REGISTRY",
    "get_available_markets",
    "create_market_rules",
]
