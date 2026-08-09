"""跨模块契约：市场规则基类与常用解析结果类型。"""

from __future__ import annotations

from core.modules.market_profile.core.base.market_base_rules import MarketBaseRules
from core.modules.market_profile.core.services.lot_size_service import LotSizeResolved

__all__ = ["MarketBaseRules", "LotSizeResolved"]
