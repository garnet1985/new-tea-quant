"""扫描命中后的贴板标注（写入 Opportunity.metadata）。

本文件:
- annotate_buy_at_limit_up / opportunity_buy_at_limit_up: 涨停买入判定
  边界: 负责 metadata 标注；不负责 market_rules 定义或 scan hook 逻辑
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.modules.market_profile.core.markets import create_market_rules
from core.modules.strategy.core.engines.shared.services.safe_values.safe_bar_value import SafeBarValue
from core.modules.strategy.core.engines.shared.data_class.opportunity import Opportunity

BUY_AT_LIMIT_UP_KEY = "buy_at_limit_up"


def annotate_buy_at_limit_up(
    opportunity: Opportunity,
    *,
    market_profile: str,
    klines: List[Dict[str, Any]],
    scan_date: Optional[str] = None,
) -> None:
    """用 trigger 价 vs 昨收判断是否贴涨停，写入 ``metadata.buy_at_limit_up``。"""
    if opportunity is None:
        return
    day = str(scan_date or opportunity.trigger_date or "").strip()
    signal_bar = _bar_on(klines, day) if day else (klines[-1] if klines else None)
    if not signal_bar:
        return
    entity_id = str(opportunity.stock.id or "").strip()
    try:
        ref = float(opportunity.trigger_price or 0.0)
    except (TypeError, ValueError):
        ref = 0.0
    if ref <= 0:
        ref = float(SafeBarValue.float(signal_bar, "close") or 0.0)
    if not entity_id or ref <= 0:
        return

    prev = SafeBarValue.optional_float(signal_bar, "pre_close")
    if prev is None or prev <= 0:
        # 尝试用前一根 bar 的 close
        idx = _bar_index(klines, day)
        if idx is not None and idx > 0:
            prev = SafeBarValue.float(klines[idx - 1], "close")
    if prev is None or prev <= 0:
        return

    profile = str(market_profile or "").strip() or "china_a_stock"
    try:
        rules = create_market_rules(profile)
        at_up = bool(rules.is_at_limit_up(ref, prev, entity_id))
    except Exception:
        at_up = False

    if not isinstance(opportunity.metadata, dict):
        opportunity.metadata = {}
    opportunity.metadata[BUY_AT_LIMIT_UP_KEY] = at_up


def opportunity_buy_at_limit_up(opportunity: Opportunity) -> Optional[bool]:
    if not isinstance(opportunity.metadata, dict):
        return None
    raw = opportunity.metadata.get(BUY_AT_LIMIT_UP_KEY)
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return bool(raw)
    text = str(raw).strip().lower()
    if text in {"1", "true", "yes"}:
        return True
    if text in {"0", "false", "no"}:
        return False
    return None


def _bar_on(klines: List[Dict[str, Any]], day: str) -> Optional[Dict[str, Any]]:
    for bar in klines or []:
        if str(bar.get("date") or "").strip() == day:
            return bar
    return None


def _bar_index(klines: List[Dict[str, Any]], day: str) -> Optional[int]:
    for i, bar in enumerate(klines or []):
        if str(bar.get("date") or "").strip() == day:
            return i
    return None


__all__ = [
    "BUY_AT_LIMIT_UP_KEY",
    "annotate_buy_at_limit_up",
    "opportunity_buy_at_limit_up",
]
