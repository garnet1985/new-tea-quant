"""Tag 模块公开 API。"""

from typing import Any

from core.modules.tag.contracts import (
    TagCalendarAsOfResult,
    TagContext,
    TagData,
    TagExecutionMode,
    TagHooks,
    TagInfo,
    TagUpdateMode,
)
from core.modules.tag.tag import Tag

__all__ = [
    "Tag",
    "TagCalendarAsOfResult",
    "TagContext",
    "TagData",
    "TagExecutionMode",
    "TagHooks",
    "TagInfo",
    "TagUpdateMode",
]


def __getattr__(name: str) -> Any:
    # AUDIT: CLI / run_tag 仍用 TagManager 名；新代码用 Tag
    if name == "TagManager":
        from core.modules.tag.tag_manager import TagManager

        return TagManager
    raise AttributeError(f"module {__name__!r} has no attribute {name}")
