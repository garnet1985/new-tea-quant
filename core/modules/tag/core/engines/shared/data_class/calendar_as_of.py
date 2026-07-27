"""Tag calendar as-of hook 返回类型（slice_based on_calendar_asof 契约）。

消费者: TagHooks, TagSliceJobExecutor
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class TagCalendarAsOfResult:
    """``on_calendar_asof`` 返回：按 entity 写出 tag。

    ``entity_tags``: entity_id → 待写入项列表，每项：
        - tag_name: str（对应 tag_definitions[].name）
        - value: tag 值
        - start_date / end_date: 可选
    """

    entity_tags: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    carry: Dict[str, Any] = field(default_factory=dict)
    as_of_date: str = ""


__all__ = ["TagCalendarAsOfResult"]
