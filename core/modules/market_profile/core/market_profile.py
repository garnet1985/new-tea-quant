#!/usr/bin/env python3
"""Market Profile Proxy — 对外统一入口（实现位于 ``core/market_profile.py``）。"""

from __future__ import annotations

from typing import Dict, List, Optional

from core.modules.market_profile.core.base.market_base_rules import MarketBaseRules
from core.modules.market_profile.core.markets import (
    MARKET_RULES_REGISTRY,
    create_market_rules,
    get_available_markets,
)


class MarketRulesProxy:
    """市场规则代理（Facade）。

    - 实例：挂载当前市场，按需懒加载各 profile 实例
    - 类方法 ``for_market``：只创建单个市场规则（跨模块推荐入口）
    """

    def __init__(self, default_market: str = "china_a_stock") -> None:
        self._mounted: Optional[MarketBaseRules] = None
        self._instances: Dict[str, MarketBaseRules] = {}
        self.set_market(default_market)

    @classmethod
    def for_market(cls, profile_id: str) -> MarketBaseRules:
        """创建单个市场规则实例（不构造 Proxy、不预加载其它市场）。"""
        return create_market_rules(profile_id)

    @classmethod
    def available_ids(cls) -> List[str]:
        """注册表中的全部市场 ID（不实例化）。"""
        return get_available_markets()

    def _ensure(self, profile_id: str) -> MarketBaseRules:
        if profile_id not in MARKET_RULES_REGISTRY:
            raise ValueError(f"Market profile '{profile_id}' not available")
        if profile_id not in self._instances:
            self._instances[profile_id] = create_market_rules(profile_id)
        return self._instances[profile_id]

    @property
    def current(self) -> MarketBaseRules:
        if self._mounted is None:
            raise RuntimeError("No market mounted")
        return self._mounted

    def set_market(self, profile_id: str) -> None:
        """挂载当前市场。

        Raises:
            ValueError: 市场不存在
        """
        self._mounted = self._ensure(profile_id)

    def get_market(self, profile_id: str) -> MarketBaseRules:
        """获取特定市场的规则实例（懒加载，同 Proxy 内单例缓存）。"""
        return self._ensure(profile_id)

    def list_available(self) -> List[str]:
        """列出所有可用市场 ID。"""
        return get_available_markets()

    def is_available(self, profile_id: str) -> bool:
        return profile_id in MARKET_RULES_REGISTRY

    def get_market_id(self) -> str:
        if self._mounted is None:
            raise RuntimeError("No market mounted")
        return self._mounted.profile_id


__all__ = ["MarketRulesProxy"]
