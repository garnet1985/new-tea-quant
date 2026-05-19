#!/usr/bin/env python3
"""涨跌停辅助计算与机会标注（无 settings 解析；profile / 策略字段由调用方传入）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.modules.market_profile.profile import MarketProfile

_LIMIT_EPS = 1e-4
_LIMIT_UP_HINT = "涨停附近，可能难以买入"


def bar_prev_close(prev_bar: Optional[Dict[str, Any]]) -> Optional[float]:
    if not prev_bar:
        return None
    try:
        px = float(prev_bar.get("close") or 0.0)
    except (TypeError, ValueError):
        return None
    return px if px > 0 else None


def signal_and_prev_bars(
    klines: List[Dict[str, Any]],
    signal_date: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if not klines or not signal_date:
        return None, None
    ordered = sorted(klines, key=lambda b: str((b or {}).get("date") or ""))
    for idx, bar in enumerate(ordered):
        if str((bar or {}).get("date") or "") == str(signal_date):
            return bar, ordered[idx - 1] if idx > 0 else None
    return None, None


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


def _set_metadata_hint(opportunity: Any, hint: str) -> None:
    meta = getattr(opportunity, "metadata", None)
    if meta is None:
        opportunity.metadata = {}
        meta = opportunity.metadata
    if isinstance(meta, dict):
        meta["tradability_hint"] = hint


def stamp_buy_tradability(
    opportunity: Any,
    profile: MarketProfile,
    stock_id: str,
    prev_bar: Optional[Dict[str, Any]],
    buy_price: float,
    *,
    hint_on_limit_up: bool = False,
) -> None:
    prev = bar_prev_close(prev_bar)
    at_limit_up = is_at_limit_up(profile, stock_id, prev, buy_price) if prev else None
    if hasattr(opportunity, "buy_prev_close"):
        opportunity.buy_prev_close = prev
    if hasattr(opportunity, "buy_at_limit_up"):
        opportunity.buy_at_limit_up = at_limit_up
    if hint_on_limit_up and at_limit_up is True:
        _set_metadata_hint(opportunity, _LIMIT_UP_HINT)


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


def should_skip_buy(
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


def should_skip_sell(
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


def annotate_scan_opportunity(
    opportunity: Any,
    *,
    profile: MarketProfile,
    klines: List[Dict[str, Any]],
    scan_date: Optional[str] = None,
) -> None:
    if opportunity is None:
        return
    signal_date = str(scan_date or getattr(opportunity, "trigger_date", None) or "").strip()
    signal_bar, prev_bar = signal_and_prev_bars(klines, signal_date)
    if signal_bar is None:
        return
    stock_id = str(getattr(opportunity, "stock_id", None) or "").strip()
    if not stock_id:
        stock = getattr(opportunity, "stock", None)
        if isinstance(stock, dict) and stock.get("id"):
            stock_id = str(stock["id"]).strip()
    try:
        ref_price = float(getattr(opportunity, "trigger_price", None) or 0.0)
    except (TypeError, ValueError):
        ref_price = 0.0
    if ref_price <= 0:
        try:
            ref_price = float(signal_bar.get("close") or 0.0)
        except (TypeError, ValueError):
            ref_price = 0.0
    if not stock_id or ref_price <= 0:
        return
    stamp_buy_tradability(
        opportunity, profile, stock_id, prev_bar, ref_price, hint_on_limit_up=True
    )


__all__ = [
    "annotate_scan_opportunity",
    "bar_prev_close",
    "is_at_limit_down",
    "is_at_limit_up",
    "row_buy_at_limit_up",
    "row_sell_at_limit_down",
    "should_skip_buy",
    "should_skip_sell",
    "signal_and_prev_bars",
    "stamp_buy_tradability",
    "stamp_target_tradability",
]
