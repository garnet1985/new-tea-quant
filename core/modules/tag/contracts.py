"""Tag 跨模块公开契约（hooks + 共享数据类型 re-export）。

本文件:
- TagHooks / TagContext / TagData: userspace hook 契约
- TagCalendarAsOfResult: slice_based 横截面返回
- TagUpdateMode / TagExecutionMode: 公开枚举
  边界: 仅类型与契约导出；不含编排实现
"""

from __future__ import annotations

from core.modules.tag.core.engines.per_entity.shared.data_class import TagCalendarAsOfResult
from core.modules.tag.core.engines.per_entity.shared.hooks import TagHooks
from core.modules.tag.core.engines.per_entity.shared.hooks.hook_params import (
    TagContext,
    TagData,
    TagInfo,
)
from core.modules.tag.core.enums import TagExecutionMode, TagUpdateMode

__all__ = [
    "TagCalendarAsOfResult",
    "TagContext",
    "TagData",
    "TagExecutionMode",
    "TagHooks",
    "TagInfo",
    "TagUpdateMode",
]
