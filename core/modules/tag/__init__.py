"""
Tag 系统：场景化标签计算与落库。

公开 API：
- TagManager.execute — 唯一执行入口
- BaseTagWorker — userspace tag_worker 基类
"""

from core.modules.tag.engines.shared.base_worker import BaseTagWorker
from core.modules.tag.tag_manager import TagManager
from core.modules.tag.enums import TagUpdateMode
from core.modules.tag.config import get_scenarios_root
from core.modules.tag.engines.sliced.types import (
    CalendarAsOfContext,
    TagCalendarAsOfResult,
)

__all__ = [
    "BaseTagWorker",
    "TagManager",
    "TagUpdateMode",
    "get_scenarios_root",
    "CalendarAsOfContext",
    "TagCalendarAsOfResult",
]
