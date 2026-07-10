#!/usr/bin/env python3
"""Market Profile Proxy - 对外暴露的统一入口。"""

from typing import Dict, List, Optional

from .core.base.market_base_rules import MarketBaseRules
from .core.markets import create_market_rules, get_available_markets


class MarketRulesProxy:
    """市场规则代理（对外暴露）。

    提供跨profile功能：
    - 发现和注册现有市场规则
    - 列出所有可用市场
    - 提供当前挂载的市场实例
    - 获取特定市场的规则实例
    """

    def __init__(self, default_market: str = "china_a_stock") -> None:
        self._mounted: Optional[MarketBaseRules] = None
        self._available: Dict[str, MarketBaseRules] = {}
        self._init_available_markets()
        self.set_market(default_market)

    def _init_available_markets(self) -> None:
        """初始化所有可用市场"""
        for profile_id in get_available_markets():
            self._available[profile_id] = create_market_rules(profile_id)

    @property
    def current(self) -> MarketBaseRules:
        """获取当前挂载的市场规则实例"""
        if self._mounted is None:
            raise RuntimeError("No market mounted")

        return self._mounted

    def set_market(self, profile_id: str) -> None:
        """挂载当前市场

        Args:
            profile_id: 市场配置ID（如 'china_a_stock', 'hong_kong'）

        Raises:
            ValueError: 市场不存在
        """
        if profile_id not in self._available:
            raise ValueError(f"Market profile '{profile_id}' not available")

        self._mounted = self._available[profile_id]


    def get_market(self, profile_id: str) -> MarketBaseRules:
        """获取特定市场的规则实例

        Args:
            profile_id: 市场配置ID

        Returns:
            MarketBaseRules实例

        Raises:
            ValueError: 市场不存在
        """
        if profile_id not in self._available:
            raise ValueError(f"Market profile '{profile_id}' not available")

        return self._available[profile_id]

    def list_available(self) -> List[str]:
        """列出所有可用市场"""
        return list(self._available.keys())

    def is_available(self, profile_id: str) -> bool:
        """判断市场是否可用"""
        return profile_id in self._available

    def get_market_id(self) -> str:
        """获取当前挂载的市场ID"""
        if self._mounted is None:
            raise RuntimeError("No market mounted")

        return self._mounted.profile_id


__all__ = ["MarketRulesProxy"]