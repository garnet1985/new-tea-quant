#!/usr/bin/env python3
"""calendar_slice 横截面：从 inject by_entity 构建 stocks 上下文。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from core.utils.date.date_utils import DateUtils


def _rows_until(
    rows: List[Mapping[str, Any]],
    as_of: str,
    *,
    time_field: str,
) -> List[Dict[str, Any]]:
    target = str(as_of or "").strip()
    if not target:
        return []
    out: List[Dict[str, Any]] = []
    for row in rows or ():
        dt = DateUtils.normalize(row.get(time_field), fmt=DateUtils.FMT_YYYYMMDD)
        if not dt or dt > target:
            continue
        out.append(dict(row))
    return out


def build_stocks_context(
    by_entity: Mapping[str, Mapping[str, Any]],
    as_of: str,
    *,
    axis_data_id: str,
    min_records: int = 1,
    time_field: str = "date",
) -> Dict[str, Dict[str, Any]]:
    """
    构建 ``on_calendar_asof`` 用的 ``stocks`` 字典。

    与 ``calculate_tag`` 的 ``historical_data`` 键一致（data_id → 截至 as_of 的行列表）。
    仅包含 as_of 当日有 axis  bar 且满足 min_records 的 entity。
    """
    axis = str(axis_data_id or "").strip()
    if not axis:
        return {}
    min_n = max(1, int(min_records or 1))
    stocks: Dict[str, Dict[str, Any]] = {}
    for eid, inject in by_entity.items():
        if not isinstance(inject, dict):
            continue
        slot_data = inject.get("slot_data") or {}
        if not isinstance(slot_data, dict):
            continue
        axis_rows = list(slot_data.get(axis) or [])
        sliced_axis = _rows_until(axis_rows, as_of, time_field=time_field)
        if not sliced_axis:
            continue
        last_dt = DateUtils.normalize(
            sliced_axis[-1].get(time_field),
            fmt=DateUtils.FMT_YYYYMMDD,
        )
        if last_dt != str(as_of).strip():
            continue
        if len(sliced_axis) < min_n:
            continue
        historical: Dict[str, Any] = {}
        overrides = inject.get("time_field_overrides") or {}
        for slot, rows in slot_data.items():
            tf = str(overrides.get(slot) or time_field)
            historical[str(slot)] = _rows_until(list(rows or []), as_of, time_field=tf)
        stocks[str(eid)] = historical
    return stocks


def axis_data_id_from_settings(settings: Dict[str, Any]) -> str:
    data = settings.get("data") or {}
    configured = str(data.get("tag_time_axis_based_on") or "").strip()
    if configured:
        return configured
    for item in data.get("required") or []:
        raw = str(item.get("data_id") or "").strip()
        if raw:
            return raw
    return "stock.kline.daily"


__all__ = ["axis_data_id_from_settings", "build_stocks_context"]
