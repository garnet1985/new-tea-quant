#!/usr/bin/env python3
"""商品期货市场规则（Commodity Future Market Rules）。"""

from typing import Any, Dict

from ..base.market_base_rules import MarketBaseRules


class CommodityFutureRules(MarketBaseRules):
    """商品期货市场规则。

    期货按品种不同涨跌幅，整手规则简单（1手起）。
    """

    @property
    def profile_id(self) -> str:
        return "commodity_future"

    @property
    def settings(self) -> Dict[str, Any]:
        """返回商品期货市场配置"""
        from .settings import settings as settings_dict
        return settings_dict

    # 期货特殊：整手规则简单（1手起，步长1）
    def is_valid_quantity(self, quantity: int) -> bool:
        """期货1手起，无整手限制"""
        return quantity >= self._default_min_lot

    def is_valid_quantity_for_stock(self, quantity: int, stock_id: str) -> bool:
        """期货1手起，无整手限制"""
        return quantity >= self._default_min_lot

    def floor_quantity(self, target_quantity: int) -> int:
        """期货无整手限制，直接返回目标数量"""
        return max(target_quantity, self._default_min_lot)

    def floor_quantity_for_stock(self, target_quantity: int, stock_id: str) -> int:
        """期货无整手限制，直接返回目标数量"""
        return max(target_quantity, self._default_min_lot)


__all__ = ["CommodityFutureRules"]