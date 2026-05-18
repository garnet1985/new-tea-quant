#!/usr/bin/env python3
"""扫描机会涨跌停标注（仅提示，不过滤）。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.modules.strategy.engines.shared.helpers.market_profile_runtime import (
    load_market_profile_for_settings,
    stamp_buy_tradability,
)

_SCAN_LIMIT_UP_HINT = "涨停附近，可能难以买入"


def _bars_for_scan_date(
    klines: List[Dict[str, Any]],
    scan_date: str,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """返回 (信号日 bar, 前一交易日 bar)。"""
    if not klines or not scan_date:
        return None, None
    ordered = sorted(klines, key=lambda b: str((b or {}).get("date") or ""))
    signal_idx = -1
    for idx, bar in enumerate(ordered):
        if str((bar or {}).get("date") or "") == str(scan_date):
            signal_idx = idx
            break
    if signal_idx < 0:
        return None, None
    signal_bar = ordered[signal_idx]
    prev_bar = ordered[signal_idx - 1] if signal_idx > 0 else None
    return signal_bar, prev_bar


def annotate_scan_opportunity(
    opportunity: Any,
    *,
    settings_dict: Dict[str, Any],
    klines: List[Dict[str, Any]],
    scan_date: Optional[str] = None,
) -> None:
    """找到机会时标注是否触及涨停（信号价相对前收），便于下游/适配器提示。"""
    if opportunity is None:
        return
    resolved_date = str(
        scan_date
        or getattr(opportunity, "trigger_date", None)
        or getattr(opportunity, "scan_date", None)
        or ""
    ).strip()
    signal_bar, prev_bar = _bars_for_scan_date(klines, resolved_date)
    if signal_bar is None:
        return

    stock_id = str(
        getattr(opportunity, "stock_id", None)
        or (getattr(opportunity, "stock", None) or {}).get("id")
        or ""
    ).strip()
    if not stock_id:
        return

    try:
        ref_price = float(getattr(opportunity, "trigger_price", None) or 0.0)
    except (TypeError, ValueError):
        ref_price = 0.0
    if ref_price <= 0:
        try:
            ref_price = float(signal_bar.get("close") or 0.0)
        except (TypeError, ValueError):
            ref_price = 0.0
    if ref_price <= 0:
        return

    profile = load_market_profile_for_settings(settings_dict)
    stamp_buy_tradability(opportunity, profile, stock_id, prev_bar, ref_price)

    if getattr(opportunity, "buy_at_limit_up", None) is True:
        meta = getattr(opportunity, "metadata", None)
        if meta is None:
            opportunity.metadata = {}
            meta = opportunity.metadata
        if isinstance(meta, dict):
            meta["tradability_hint"] = _SCAN_LIMIT_UP_HINT


__all__ = [
    "annotate_scan_opportunity",
    "_bars_for_scan_date",
]
