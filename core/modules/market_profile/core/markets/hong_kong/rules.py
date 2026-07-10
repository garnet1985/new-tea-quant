#!/usr/bin/env python3
"""港股市场规则（Hong Kong Market Rules）。"""

from typing import Any, Dict

from ..base.market_base_rules import MarketBaseRules


class HongKongRules(MarketBaseRules):
    """港股市场规则。

    港股无涨跌幅限制，需要覆盖is_within_price_limit方法。
    """

    @property
    def profile_id(self) -> str:
        return "hong_kong"

    @property
    def settings(self) -> Dict[str, Any]:
        """返回港股市场配置"""
        from .settings import settings as settings_dict
        return settings_dict

    # 港股特殊：无涨跌幅限制
    def is_within_price_limit(self, current_price: float, prev_close: float) -> bool:
        """港股无涨跌幅限制，始终返回True"""
        return True

    def is_within_price_limit_for_stock(
        self, current_price: float, prev_close: float, stock_id: str, status_tags=None
    ) -> bool:
        """港股无涨跌幅限制，始终返回True"""
        return True


__all__ = ["HongKongRules"]