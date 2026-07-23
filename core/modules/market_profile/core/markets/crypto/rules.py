#!/usr/bin/env python3
"""数字货币市场规则（Crypto Market Rules）。"""

from typing import Any, Dict

from ...base.market_base_rules import MarketBaseRules


class CryptoRules(MarketBaseRules):
    """数字货币市场规则。

    数字货币无涨跌幅限制，24小时交易，极小单位起。
    """

    @property
    def profile_id(self) -> str:
        return "crypto"

    @property
    def settings(self) -> Dict[str, Any]:
        """返回数字货币市场配置"""
        from .settings import settings as settings_dict
        return settings_dict

    # 数字货币特殊：无涨跌幅限制
    def is_within_price_limit(self, current_price: float, prev_close: float) -> bool:
        """数字货币无涨跌幅限制，始终返回True"""
        return True

    def is_within_price_limit_for_stock(
        self, current_price: float, prev_close: float, stock_id: str, status_tags=None
    ) -> bool:
        """数字货币无涨跌幅限制，始终返回True"""
        return True

    # 数字货币特殊：整手规则简单（1单位起）
    def is_valid_quantity(self, quantity: int) -> bool:
        """数字货币1单位起，无整手限制"""
        return quantity >= self._default_min_lot

    def is_valid_quantity_for_stock(self, quantity: int, stock_id: str) -> bool:
        """数字货币1单位起，无整手限制"""
        return quantity >= self._default_min_lot

    def floor_quantity(self, target_quantity: int) -> int:
        """数字货币无整手限制，直接返回目标数量"""
        return max(target_quantity, self._default_min_lot)

    def floor_quantity_for_stock(self, target_quantity: int, stock_id: str) -> int:
        """数字货币无整手限制，直接返回目标数量"""
        return max(target_quantity, self._default_min_lot)


__all__ = ["CryptoRules"]