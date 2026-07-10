#!/usr/bin/env python3
"""外汇市场规则（Forex Market Rules）。"""

from typing import Any, Dict

from ..base.market_base_rules import MarketBaseRules


class ForexRules(MarketBaseRules):
    """外汇市场规则。

    外汇无涨跌幅限制，整手规则特殊（标准手100,000）。
    """

    @property
    def profile_id(self) -> str:
        return "forex"

    @property
    def settings(self) -> Dict[str, Any]:
        """返回外汇市场配置"""
        from .settings import settings as settings_dict
        return settings_dict

    # 外汇特殊：无涨跌幅限制
    def is_within_price_limit(self, current_price: float, prev_close: float) -> bool:
        """外汇无涨跌幅限制，始终返回True"""
        return True

    def is_within_price_limit_for_stock(
        self, current_price: float, prev_close: float, stock_id: str, status_tags=None
    ) -> bool:
        """外汇无涨跌幅限制，始终返回True"""
        return True

    # 外汇特殊：整手规则（标准手）
    def is_valid_quantity(self, quantity: int) -> bool:
        """外汇标准手，必须是最小单位的倍数"""
        return quantity >= self._default_min_lot and (quantity % self._default_lot_step == 0)

    def is_valid_quantity_for_stock(self, quantity: int, stock_id: str) -> bool:
        """外汇标准手，必须是最小单位的倍数"""
        return self.is_valid_quantity(quantity)

    def floor_quantity(self, target_quantity: int) -> int:
        """计算符合标准手的数量"""
        if target_quantity < self._default_min_lot:
            return 0
        steps = target_quantity // self._default_lot_step
        return steps * self._default_lot_step

    def floor_quantity_for_stock(self, target_quantity: int, stock_id: str) -> int:
        """计算符合标准手的数量"""
        return self.floor_quantity(target_quantity)


__all__ = ["ForexRules"]