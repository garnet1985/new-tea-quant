#!/usr/bin/env python3
"""simulation.skip_investment_when — 价格/资金模拟跳过（不删枚举行）。"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.strategy.engines.shared.helpers.stock_status_exit import (
    STOCK_STATUS_PREFIX,
)

KNOWN_SKIP_INVESTMENT_TAGS = frozenset({"st", "star_st"})
METADATA_TAGS_KEY = "stock_status_at_trigger"
ROW_SKIP_REASON_KEY = "sim_skip_investment_reason"


def parse_skip_investment_when(raw: Any) -> Tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError("simulation.skip_investment_when 必须为 list")
    out: List[str] = []
    for idx, item in enumerate(raw):
        tag = str(item or "").strip().lower()
        if not tag:
            continue
        if tag not in KNOWN_SKIP_INVESTMENT_TAGS:
            raise ValueError(
                f"simulation.skip_investment_when[{idx}] 非法: {item!r}；"
                f"允许: {sorted(KNOWN_SKIP_INVESTMENT_TAGS)}"
            )
        if tag not in out:
            out.append(tag)
    return tuple(out)


def _parse_tags_value(raw: Any) -> List[str]:
    if raw is None or raw == "":
        return []
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                raw = json.loads(text)
            except json.JSONDecodeError:
                return []
        else:
            return [text.lower()]
    if not isinstance(raw, list):
        return []
    return [str(x).strip().lower() for x in raw if str(x).strip()]


def active_tags_at_trigger_from_row(row: Dict[str, Any]) -> List[str]:
    """CSV 扁平列 ``stock_status_at_trigger`` 优先，其次 ``metadata`` 内嵌。"""
    flat = _parse_tags_value(row.get(METADATA_TAGS_KEY))
    if flat:
        return flat
    meta = row.get("metadata")
    if isinstance(meta, str) and meta.strip():
        try:
            meta = json.loads(meta)
        except json.JSONDecodeError:
            meta = None
    if not isinstance(meta, dict):
        return []
    return _parse_tags_value(meta.get(METADATA_TAGS_KEY))


def stock_status_tags_csv_value(opportunity: Dict[str, Any]) -> str:
    """枚举写 CSV 时序列化触发日状态标签。"""
    tags = active_tags_at_trigger_from_row(
        {"metadata": opportunity.get("metadata")}
    )
    if not tags:
        return ""
    return json.dumps(tags, ensure_ascii=False)


def should_skip_investment(
    row: Dict[str, Any],
    skip_when: Sequence[str],
) -> Optional[str]:
    """
    若触发日状态命中 ``skip_when`` 中任一项，返回 skip 原因（``stock_status:st`` 等）。
    依赖枚举写入的 ``metadata.stock_status_at_trigger``。
    """
    if not skip_when:
        return None
    active = set(active_tags_at_trigger_from_row(row))
    if not active:
        return None
    for tag in skip_when:
        key = str(tag or "").strip().lower()
        if key in active:
            return f"{STOCK_STATUS_PREFIX}{key}"
    return None


def stamp_stock_status_at_trigger(
    opportunity: Any,
    *,
    trade_date: str,
    tier_periods: Dict[str, List[Dict[str, Any]]],
) -> None:
    """枚举器在机会创建时写入触发日股票状态标签（供下游 skip，不删机会）。"""
    from core.tables.stock.stock_st_periods.st_period_rules import (
        TIER_STAR_ST,
        TIER_ST,
        is_tier_active_on,
    )

    tags: List[str] = []
    day = str(trade_date or "").strip()
    if not day:
        return
    if is_tier_active_on(tier_periods.get(TIER_ST) or [], day, tier=TIER_ST):
        tags.append(TIER_ST)
    if is_tier_active_on(tier_periods.get(TIER_STAR_ST) or [], day, tier=TIER_STAR_ST):
        tags.append(TIER_STAR_ST)
    if not tags:
        return
    meta = getattr(opportunity, "metadata", None)
    if meta is None or not isinstance(meta, dict):
        opportunity.metadata = {}
        meta = opportunity.metadata
    meta[METADATA_TAGS_KEY] = tags


__all__ = [
    "KNOWN_SKIP_INVESTMENT_TAGS",
    "METADATA_TAGS_KEY",
    "ROW_SKIP_REASON_KEY",
    "active_tags_at_trigger_from_row",
    "parse_skip_investment_when",
    "should_skip_investment",
    "stamp_stock_status_at_trigger",
    "stock_status_tags_csv_value",
]
