"""
Tag 系统：场景化标签计算与落库。

公开 API：
- TagManager.execute — 唯一执行入口
- BaseTagWorker — userspace tag_worker 基类
"""

from typing import Any

from core.modules.tag.enums import TagUpdateMode
from core.modules.tag.config import get_scenarios_root

__all__ = [
    "BaseTagWorker",
    "TagManager",
    "TagUpdateMode",
    "get_scenarios_root",
    "CalendarAsOfContext",
    "TagCalendarAsOfResult",
]


def __getattr__(name: str) -> Any:
    if name == "TagManager":
        from core.modules.tag.tag_manager import TagManager

        return TagManager
    if name == "BaseTagWorker":
        from core.modules.tag.engines.shared.base_worker import BaseTagWorker

        return BaseTagWorker
    if name in {"CalendarAsOfContext", "TagCalendarAsOfResult"}:
        from core.modules.tag.engines.sliced.types import (
            CalendarAsOfContext,
            TagCalendarAsOfResult,
        )

        return {
            "CalendarAsOfContext": CalendarAsOfContext,
            "TagCalendarAsOfResult": TagCalendarAsOfResult,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
