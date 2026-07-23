#!/usr/bin/env python3
"""calendar_slice 横截面：基于 DataCursor 构建实体上下文（通用，不限于股票）。"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from core.utils.date.date_utils import DateUtils
from core.modules.data_cursor import DataCursor


class EntityDataContext:
    """单实体带时间索引的运行时上下文。

    使用 DataCursor 实现高效的时间序列切片查询（O(K) 游标推进），
    替代原来的线性扫描方式 (_rows_until) O(N×M×L)。
    """

    def __init__(
        self,
        slot_data: Dict[str, list],
        time_field_overrides: Optional[Dict[str, str]] = None,
    ):
        self._cursor = DataCursor.from_rows(
            rows_by_source=slot_data,
            time_field_overrides=time_field_overrides,
        )

    def get_data_until(self, as_of: str) -> Dict[str, list]:
        """O(K) 获取截至 as_of 的数据（K=自上次调用后的新增行数）。"""
        return self._cursor.until(as_of)

    def reset(self) -> None:
        """重置游标（新切片开始时调用，避免跨切片累积数据）。"""
        self._cursor.reset()


def build_entity_contexts(
    by_entity: Mapping[str, Mapping[str, Any]],
) -> Dict[str, EntityDataContext]:
    """为所有实体预构建 DataCursor（只做一次，在切片开始时调用）。"""
    contexts: Dict[str, EntityDataContext] = {}

    for eid, inject in by_entity.items():
        if not isinstance(inject, dict):
            continue
        slot_data = inject.get("slot_data") or {}
        if not isinstance(slot_data, dict):
            continue
        overrides = inject.get("time_field_overrides")
        contexts[eid] = EntityDataContext(
            slot_data=slot_data,
            time_field_overrides=overrides,
        )

    return contexts


def build_entity_historical_context(
    as_of: str,
    *,
    axis_data_id: str,
    min_records: int = 1,
    entity_contexts: Dict[str, EntityDataContext],
) -> Dict[str, Dict[str, Any]]:
    """使用 DataCursor 构建 on_calendar_asof 用的实体历史数据字典。

    Args:
        as_of: 截至日期
        axis_data_id: 时间轴数据源 ID
        min_records: 最小记录数要求
        entity_contexts: 预构建的 DataCursor 上下文

    Returns:
        entity_id → historical 数据字典（仅包含满足条件的实体）
    """
    axis = str(axis_data_id or "").strip()
    if not axis:
        return {}

    min_n = max(1, int(min_records or 1))
    entities: Dict[str, Dict[str, Any]] = {}

    for eid, ctx in entity_contexts.items():
        try:
            historical = ctx.get_data_until(as_of)
            axis_rows = historical.get(axis) or []
            if not axis_rows:
                continue

            last_dt = DateUtils.normalize(
                axis_rows[-1].get("date"),
                fmt=DateUtils.FMT_YYYYMMDD,
            )
            if last_dt != str(as_of).strip():
                continue
            if len(axis_rows) < min_n:
                continue

            entities[eid] = historical
        except Exception:
            continue

    return entities


def axis_data_id_from_settings(settings: Dict[str, Any]) -> str:
    """从 settings 中提取时间轴数据源 ID。"""
    data = settings.get("data") or {}
    configured = str(data.get("tag_time_axis_based_on") or "").strip()
    if configured:
        return configured
    for item in data.get("required") or []:
        raw = str(item.get("data_id") or "").strip()
        if raw:
            return raw
    return "stock.kline.daily"


__all__ = [
    "EntityDataContext",
    "build_entity_contexts",
    "build_entity_historical_context",
    "axis_data_id_from_settings",
]
