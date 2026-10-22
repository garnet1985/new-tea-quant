"""将扫描侧机会映射为协议 ScanSessionReport（不 import strategy）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from core.modules.post_process.core.protocol import (
    Opportunity,
    ScanSessionReport,
    StrategyScanReport,
)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def opportunity_from_scan_item(
    item: Any,
    *,
    strategy_name: str = "",
    index: int = 0,
) -> Opportunity:
    """Duck-type 映射策略内部 Opportunity（或已是协议 Opportunity）。"""
    if isinstance(item, Opportunity):
        return item

    stock = getattr(item, "stock", None)
    entity_id = str(getattr(item, "stock_id", "") or "").strip()
    entity_name = str(getattr(item, "stock_name", "") or "").strip()
    entity_exchange = ""
    entity_type = ""
    if stock is not None:
        entity_id = entity_id or str(getattr(stock, "id", "") or "").strip()
        entity_name = entity_name or str(getattr(stock, "name", "") or "").strip()
        entity_exchange = str(getattr(stock, "exchange_center", "") or "").strip()
        entity_type = str(getattr(stock, "type", "") or "").strip()

    trigger_date = str(getattr(item, "trigger_date", "") or "").strip()
    trigger_price = _float(getattr(item, "trigger_price", 0.0))
    trigger_price_raw = _float(getattr(item, "trigger_price_raw", 0.0))
    trigger_price_hfq = _float(getattr(item, "trigger_price_hfq", 0.0))

    meta = getattr(item, "meta", None)
    opp_id = ""
    if meta is not None:
        opp_id = str(getattr(meta, "opportunity_id", "") or "").strip()
    if not opp_id:
        opp_id = str(index)

    strategy = strategy_name or ""
    contributor = getattr(item, "contributor", None)
    if contributor is not None and not strategy:
        strategy = str(getattr(contributor, "strategy_name", "") or "").strip()

    protocol_id = f"{strategy}:{entity_id}:{trigger_date}:{opp_id}".strip(":")
    snapshot = getattr(item, "signal_snapshot", None)
    if not isinstance(snapshot, dict):
        snapshot = {}

    return Opportunity(
        id=protocol_id or f"opp-{index}",
        entity_id=entity_id,
        entity_name=entity_name,
        entity_exchange=entity_exchange,
        entity_type=entity_type,
        trigger_date=trigger_date,
        trigger_price=trigger_price,
        trigger_price_raw=trigger_price_raw,
        trigger_price_hfq=trigger_price_hfq,
        snapshot=dict(snapshot),
    )


def goal_summary_from_settings(goal_block: Any) -> Dict[str, Any]:
    """从策略 settings.goal 取摘要 dict；非 dict 则 {}。"""
    if not isinstance(goal_block, dict):
        return {}
    out: Dict[str, Any] = {}
    for key in ("stop_loss", "take_profit", "expiration", "protect_loss", "dynamic_loss"):
        if key in goal_block:
            out[key] = goal_block.get(key)
    return out


def build_session_report(
    *,
    scan_date: str,
    strategy_name: str,
    opportunities: Sequence[Any],
    goal: Optional[Dict[str, Any]] = None,
    strategy_version: str = "",
    emitted_at: str = "",
) -> ScanSessionReport:
    """单策略会话：strategies 长度为 1。"""
    day = str(scan_date or "").strip()
    name = str(strategy_name or "").strip()
    emitted = str(emitted_at or "").strip() or datetime.now().isoformat()
    mapped: List[Opportunity] = [
        opportunity_from_scan_item(item, strategy_name=name, index=i)
        for i, item in enumerate(list(opportunities or []), start=1)
    ]
    strategy_report = StrategyScanReport(
        strategy_name=name,
        strategy_version=str(strategy_version or ""),
        scan_date=day,
        emitted_at=emitted,
        goal=dict(goal or {}),
        opportunities=mapped,
    )
    return ScanSessionReport(
        scan_date=day,
        emitted_at=emitted,
        strategies=[strategy_report],
    )


__all__ = [
    "build_session_report",
    "goal_summary_from_settings",
    "opportunity_from_scan_item",
]
