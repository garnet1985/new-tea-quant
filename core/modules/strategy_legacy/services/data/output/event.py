#!/usr/bin/env python3
"""Output-side event DTO for simulator artifact streams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


def opportunity_slice_date(opportunity: Dict[str, Any]) -> str:
    """回测时间窗切片：有成交日用 ``buy_date``，否则用 ``trigger_date``（未完成机会）。"""
    buy = str(opportunity.get("buy_date") or "").strip()
    if buy:
        return buy
    return str(opportunity.get("trigger_date") or "").strip()


def parse_opportunity_buy_fill(
    opportunity: Dict[str, Any],
) -> Optional[Tuple[str, float]]:
    """真实成交：``buy_date`` 与 ``buy_price`` 均须有效；否则 ``None``（下游应跳过）。"""
    buy_date = str(opportunity.get("buy_date") or "").strip()
    if not buy_date:
        return None
    try:
        buy_price = float(opportunity.get("buy_price") or 0.0)
    except (TypeError, ValueError):
        return None
    if buy_price <= 0:
        return None
    return buy_date, buy_price


def opportunity_buy_event_date(opportunity: Dict[str, Any]) -> str:
    """资金回放买入事件日：仅 ``buy_date``；无有效成交则空字符串。"""
    parsed = parse_opportunity_buy_fill(opportunity)
    return parsed[0] if parsed else ""


@dataclass
class SimulationEvent:
    event_type: str
    date: str
    stock_id: str
    opportunity_id: str
    opportunity: Optional[Dict[str, Any]] = None
    target: Optional[Dict[str, Any]] = None

    def is_trigger(self) -> bool:
        return self.event_type == "trigger"

    def is_target(self) -> bool:
        return self.event_type == "target"


__all__ = [
    "SimulationEvent",
    "opportunity_buy_event_date",
    "opportunity_slice_date",
    "parse_opportunity_buy_fill",
]
