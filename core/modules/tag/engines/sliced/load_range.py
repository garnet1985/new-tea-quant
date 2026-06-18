#!/usr/bin/env python3
"""Tag calendar_slice 数据加载区间（lookback / load_start）。"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.strategy.engines.simulator.enumerator.stock_based.worker import (
    enumeration_actual_start_date,
)

_DEFAULT_LOOKBACK_RECORDS = 60


def parse_tag_lookback_records(job_payload: Dict[str, Any]) -> int:
    settings = job_payload.get("settings") or {}
    raw = settings.get("incremental_required_records_before_as_of_date")
    if raw is None:
        return _DEFAULT_LOOKBACK_RECORDS
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return _DEFAULT_LOOKBACK_RECORDS


def tag_slice_load_start(window_start: str, job_payload: Dict[str, Any]) -> str:
    lookback = parse_tag_lookback_records(job_payload)
    if lookback <= 0:
        return window_start
    return enumeration_actual_start_date(window_start, max(1, lookback))


__all__ = ["parse_tag_lookback_records", "tag_slice_load_start"]
