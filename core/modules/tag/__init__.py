"""
Tag 系统：场景化标签计算与落库。

公开 API：
- Tag / TagManager.execute — 执行入口
- TagHooks — userspace ``tag.py`` 基类
"""

from typing import Any

from core.modules.tag.core.enums import TagUpdateMode
from core.modules.tag.config import get_scenarios_root

__all__ = [
    "Tag",
    "TagManager",
    "TagHooks",
    "TagUpdateMode",
    "get_scenarios_root",
    "TagCalendarAsOfResult",
]


def __getattr__(name: str) -> Any:
    if name == "Tag":
        from core.modules.tag.core.tag import Tag

        return Tag
    if name == "TagManager":
        from core.modules.tag.tag_manager import TagManager

        return TagManager
    if name == "TagHooks":
        from core.modules.tag.core.engines.shared.hooks import TagHooks

        return TagHooks
    if name == "TagCalendarAsOfResult":
        from core.modules.tag.core.engines.shared.data_class import TagCalendarAsOfResult

        return TagCalendarAsOfResult
    if name == "BaseTagWorker":
        # 旧 API；保留懒加载供未迁移 userspace
        from core.modules.tag.engines.shared.base_worker import BaseTagWorker

        return BaseTagWorker
    if name in {"CalendarAsOfContext"}:
        from core.modules.tag.engines.sliced.types import CalendarAsOfContext

        return CalendarAsOfContext
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
