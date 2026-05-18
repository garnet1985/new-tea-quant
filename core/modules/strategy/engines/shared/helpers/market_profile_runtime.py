#!/usr/bin/env python3
"""策略运行时：market profile 加载、涨跌停标注（enum）与成交过滤（price / capital）。"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

from core.modules.market_profile import get_market_profile
from core.modules.market_profile.constants import DEFAULT_PROFILE_ID
from core.modules.market_profile.profile import MarketProfile

_LIMIT_EPS = 1e-4


def resolve_market_profile_id(settings: Dict[str, Any]) -> str:
    raw = (
        settings.get("market_profile", DEFAULT_PROFILE_ID)
        if isinstance(settings, dict)
        else None
    )
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


def is_at_limit_up(
    profile: MarketProfile,
    stock_id: str,
    prev_close: Optional[float],
    buy_price: float,
) -> bool:
    if prev_close is None or prev_close <= 0 or buy_price <= 0:
        return False
    try:
        limit_up, _ = profile.compute_limit_prices(stock_id, prev_close)
    except KeyError:
        return False
    return buy_price >= limit_up - _LIMIT_EPS


def is_at_limit_down(
    profile: MarketProfile,
    stock_id: str,
    prev_close: Optional[float],
    sell_price: float,
) -> bool:
    if prev_close is None or prev_close <= 0 or sell_price <= 0:
        return False
    try:
        _, limit_down = profile.compute_limit_prices(stock_id, prev_close)
    except KeyError:
        return False
    return sell_price <= limit_down + _LIMIT_EPS


def stamp_buy_tradability(
    opportunity: Any,
    profile: MarketProfile,
    stock_id: str,
    prev_bar: Optional[Dict[str, Any]],
    buy_price: float,
) -> None:
    """枚举阶段仅标注，不决定是否保留机会。"""
    prev = bar_prev_close(prev_bar)
    at_limit_up = is_at_limit_up(profile, stock_id, prev, buy_price) if prev else None
    if hasattr(opportunity, "buy_prev_close"):
        opportunity.buy_prev_close = prev
    if hasattr(opportunity, "buy_at_limit_up"):
        opportunity.buy_at_limit_up = at_limit_up


def stamp_target_tradability(
    target: Dict[str, Any],
    profile: MarketProfile,
    stock_id: str,
    prev_bar: Optional[Dict[str, Any]],
    sell_price: float,
) -> None:
    prev = bar_prev_close(prev_bar)
    target["sell_prev_close"] = prev if prev is not None else ""
    target["sell_at_limit_down"] = (
        is_at_limit_down(profile, stock_id, prev, sell_price) if prev else False
    )


def _coerce_bool(raw: Any) -> Optional[bool]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    text = str(raw).strip().lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no"):
        return False
    return None


def row_buy_at_limit_up(row: Dict[str, Any]) -> Optional[bool]:
    return _coerce_bool(row.get("buy_at_limit_up"))


def row_sell_at_limit_down(target_or_row: Dict[str, Any]) -> Optional[bool]:
    return _coerce_bool(target_or_row.get("sell_at_limit_down"))


def tradability_from_simulation_config(config: Dict[str, Any]) -> tuple[bool, bool]:
    """返回 ``(allow_buy_at_limit_up, allow_sell_at_limit_down)``。"""
    sim = config.get("simulation") if isinstance(config, dict) else None
    if not isinstance(sim, dict):
        return True, True
    edges = sim.get("edges")
    if isinstance(edges, dict):
        if "allow_buy_at_limit_up" in edges:
            allow_buy = bool(edges.get("allow_buy_at_limit_up"))
        elif "skip_limit_up_buy" in edges:
            allow_buy = not bool(edges.get("skip_limit_up_buy"))
        else:
            allow_buy = bool(sim.get("allow_buy_at_limit_up", True))
        if "allow_sell_at_limit_down" in edges:
            allow_sell = bool(edges.get("allow_sell_at_limit_down"))
        elif "skip_limit_down_sell" in edges:
            allow_sell = not bool(edges.get("skip_limit_down_sell"))
        else:
            allow_sell = bool(sim.get("allow_sell_at_limit_down", True))
        return allow_buy, allow_sell
    allow_buy = bool(sim.get("allow_buy_at_limit_up", True))
    allow_sell = bool(sim.get("allow_sell_at_limit_down", True))
    if "skip_limit_up_buy" in sim:
        allow_buy = not bool(sim.get("skip_limit_up_buy"))
    if "skip_limit_down_sell" in sim:
        allow_sell = not bool(sim.get("skip_limit_down_sell"))
    return allow_buy, allow_sell


def should_skip_buy_for_tradability(
    row: Dict[str, Any],
    profile: MarketProfile,
    stock_id: str,
    buy_price: float,
    *,
    allow_at_limit: bool,
) -> bool:
    if allow_at_limit:
        return False
    flagged = row_buy_at_limit_up(row)
    if flagged is True:
        return True
    if flagged is False:
        return False
    try:
        prev = float(row.get("buy_prev_close") or 0.0)
    except (TypeError, ValueError):
        prev = None
    if prev is None or prev <= 0:
        return False
    return is_at_limit_up(profile, stock_id, prev, buy_price)


def should_skip_sell_for_tradability(
    target_row: Dict[str, Any],
    profile: MarketProfile,
    stock_id: str,
    sell_price: float,
    *,
    allow_at_limit: bool,
) -> bool:
    if allow_at_limit:
        return False
    flagged = row_sell_at_limit_down(target_row)
    if flagged is True:
        return True
    if flagged is False:
        return False
    try:
        prev = float(target_row.get("sell_prev_close") or 0.0)
    except (TypeError, ValueError):
        prev = None
    if prev is None or prev <= 0:
        return False
    return is_at_limit_down(profile, stock_id, prev, sell_price)


__all__ = [
    "bar_prev_close",
    "is_at_limit_down",
    "is_at_limit_up",
    "load_market_profile_for_settings",
    "resolve_market_profile_id",
    "row_buy_at_limit_up",
    "row_sell_at_limit_down",
    "should_skip_buy_for_tradability",
    "should_skip_sell_for_tradability",
    "stamp_buy_tradability",
    "stamp_target_tradability",
    "tradability_from_simulation_config",
]
