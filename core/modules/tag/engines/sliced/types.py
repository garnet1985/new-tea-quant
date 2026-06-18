#!/usr/bin/env python3
"""Tag calendar_slice 用户 API 类型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.types import (
    CalendarAsOfContext,
    CalendarAsOfResult,
)


@dataclass
class TagCalendarAsOfResult:
    """
    ``on_calendar_asof`` 返回：按 entity 写出 tag。

    entity_tags: entity_id → 待写入项列表，每项：
        - tag_name: str（对应 settings.tags[].name）
        - value: tag 值（str / dict / list）
        - start_date / end_date: 可选
    """

    entity_tags: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    carry: Dict[str, Any] = field(default_factory=dict)


__all__ = [
    "CalendarAsOfContext",
    "CalendarAsOfResult",
    "TagCalendarAsOfResult",
]
