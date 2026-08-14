#!/usr/bin/env python3
"""美股市场规则（US Stock Market Rules）。"""

from typing import Any, Dict

from ...base.market_base_rules import MarketBaseRules


class USStockRules(MarketBaseRules):
    """美股市场规则。

    美股无涨跌幅限制，整手规则简单（1股起）。
    """

    @property
    def profile_id(self) -> str:
        return "us_stock"

    @property
    def settings(self) -> Dict[str, Any]:
        """返回美股市场配置"""
        from .settings import settings as settings_dict
        return settings_dict

    # 美股特殊：无涨跌幅限制
    def is_within_price_limit(self, current_price: float, prev_close: float) -> bool:
        """美股无涨跌幅限制，始终返回True"""
        return True

    def is_within_price_limit_for_stock(
        self, current_price: float, prev_close: float, stock_id: str, status_tags=None
    ) -> bool:
        """美股无涨跌幅限制，始终返回True"""
        return True

    # 美股特殊：整手规则简单（1股起，步长1）
    def is_valid_quantity(self, quantity: int) -> bool:
        """美股1股起，无整手限制"""
        return quantity >= self._default_min_lot

    def is_valid_quantity_for_stock(self, quantity: int, stock_id: str) -> bool:
        """美股1股起，无整手限制"""
        return quantity >= self._default_min_lot

    def floor_quantity(self, target_quantity: int) -> int:
        """美股无整手限制，直接返回目标数量"""
        return max(target_quantity, self._default_min_lot)

    def floor_quantity_for_stock(self, target_quantity: int, stock_id: str) -> int:
        """美股无整手限制，直接返回目标数量"""
        return max(target_quantity, self._default_min_lot)


__all__ = ["USStockRules"]