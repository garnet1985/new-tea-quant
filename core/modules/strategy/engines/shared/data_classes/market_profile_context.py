#!/usr/bin/env python3
"""回测 flow 用：由 StrategySettings 解析出的 MarketProfile 实例。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from core.modules.market_profile import get_market_profile
from core.modules.market_profile.profile import MarketProfile

if TYPE_CHECKING:
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
        StrategySettingsView,
    )
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.market_profile_settings import (
        StrategyMarketProfileSettings,
    )
    from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
        StrategySettings,
    )


@dataclass(frozen=True)
class MarketProfileContext:
    """与 ``StrategySettings`` 并列注入 flow；仅承载已合并的 profile 能力对象。"""

    profile_id: str
    profile: MarketProfile

    @classmethod
    def from_settings(cls, settings: "StrategySettings") -> "MarketProfileContext":
        mp = settings.market_profile
        return cls.from_market_profile_settings(mp)

    @classmethod
    def from_market_profile_settings(
        cls, mp_settings: "StrategyMarketProfileSettings"
    ) -> "MarketProfileContext":
        pid = str(mp_settings.profile_id or "").strip()
        return cls(profile_id=pid, profile=get_market_profile(pid))

    @classmethod
    def from_settings_view(cls, view: "StrategySettingsView") -> "MarketProfileContext":
        pid = view.market_profile
        return cls(profile_id=pid, profile=get_market_profile(pid))


__all__ = ["MarketProfileContext"]
