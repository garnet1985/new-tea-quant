"""市场制度配置（``modules.market_profile``）。

公开门面::

    from core.modules.market_profile import MarketRulesProxy

规则基类 / 类型::

    from core.modules.market_profile.contracts import MarketBaseRules, LotSizeResolved
"""

from core.modules.market_profile.core.market_profile import MarketRulesProxy

__all__ = ["MarketRulesProxy"]
