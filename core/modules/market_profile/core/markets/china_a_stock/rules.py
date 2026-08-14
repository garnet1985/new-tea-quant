#!/usr/bin/env python3
"""中国A股市场规则（China A Stock Market Rules）。"""

from typing import Any, Dict

from ...base.market_base_rules import MarketBaseRules


class ChinaAStockRules(MarketBaseRules):
    """中国A股市场规则。

    只需提供settings和profile_id，其他方法由基类提供默认实现。
    """

    @property
    def profile_id(self) -> str:
        return "china_a_stock"

    @property
    def settings(self) -> Dict[str, Any]:
        """返回A股市场配置"""
        from .settings import settings as settings_dict
        return settings_dict

    # A股规则与基类默认实现一致，无需覆盖


__all__ = ["ChinaAStockRules"]