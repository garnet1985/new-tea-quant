"""Tag calendar as-of hook 返回类型（slice_based ``on_calendar_asof`` 契约）。

命名与 strategy 对齐：
- 钩子 / 复合标识：``asof``（``on_calendar_asof``、``asof_ctx``、``asof_result``）
- 日期字段 / 变量：``as_of`` / ``as_of_date``
- 跨日状态：``session_state``（同 ``CalendarAsOfResult``）
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

    as_of_date: str = ""
    entity_tags: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    session_state: Dict[str, Any] = field(default_factory=dict)


__all__ = ["TagCalendarAsOfResult"]
