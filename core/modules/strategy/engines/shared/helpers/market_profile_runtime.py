#!/usr/bin/env python3
"""策略运行时：从 settings 加载 market profile 与涨跌停辅助判断。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.market_profile import get_market_profile
from core.modules.market_profile.constants import DEFAULT_PROFILE_ID
from core.modules.market_profile.profile import MarketProfile

_LIMIT_EPS = 1e-4


def resolve_market_profile_id(settings: Dict[str, Any]) -> str:
    raw = settings.get("market_profile", DEFAULT_PROFILE_ID) if isinstance(settings, dict) else None
    return str(raw or DEFAULT_PROFILE_ID).strip() or DEFAULT_PROFILE_ID


def load_market_profile_for_settings(settings: Dict[str, Any]) -> MarketProfile:
    return get_market_profile(resolve_market_profile_id(settings))


def bar_prev_close(prev_bar: Optional[Dict[str, Any]]) -> Optional[float]:
    if not prev_bar:
        return None
    try:
        px = float(prev_bar.get("close") or 0.0)
    except (TypeError, ValueError):
        return None
    return px if px > 0 else None


def should_skip_limit_up_buy(
    profile: MarketProfile,
    stock_id: str,
    prev_close: Optional[float],
    buy_price: float,
    *,
    enabled: bool,
) -> bool:
    if not enabled or prev_close is None or prev_close <= 0 or buy_price <= 0:
        return False
    limit_up, _ = profile.compute_limit_prices(stock_id, prev_close)
    return buy_price >= limit_up - _LIMIT_EPS


def should_skip_limit_down_sell(
    profile: MarketProfile,
    stock_id: str,
    prev_close: Optional[float],
    sell_price: float,
    *,
    enabled: bool,
) -> bool:
    if not enabled or prev_close is None or prev_close <= 0 or sell_price <= 0:
        return False
    _, limit_down = profile.compute_limit_prices(stock_id, prev_close)
    return sell_price <= limit_down + _LIMIT_EPS


__all__ = [
    "bar_prev_close",
    "load_market_profile_for_settings",
    "resolve_market_profile_id",
    "should_skip_limit_down_sell",
    "should_skip_limit_up_buy",
]
