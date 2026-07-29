"""用户 TagHooks 抽象基类（userspace ``tag.py`` 继承）。

消费者: discovery.TagHooksLoader, TagHookRuntime, slice/entity engines

本文件:
- TagHooks: calculate_tag / on_calendar_asof
  边界: 定义 hooks 契约；不负责加载、settings 或引擎编排
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING

from core.modules.tag.core.engines.per_entity.shared.data_class.calendar_as_of import (
    TagCalendarAsOfResult,
)

if TYPE_CHECKING:
    from core.modules.tag.core.engines.per_entity.shared.hooks.hook_params import TagContext


class TagHooks(ABC):
    """用户 Tag hooks 基类。"""

    @abstractmethod
    def calculate_tag(self, ctx: "TagContext") -> Optional[Dict[str, Any]]:
        """单实体 × 单 TagDefinition 打标。

        约定：
        - ``ctx.data.now`` / ``ctx.data.items`` / ``ctx.data.entity_id``
        - ``ctx.data.tag_definition`` 当前定义
        - 可变状态写入 ``ctx.custom``
        - 返回 ``{value, start_date?, end_date?}`` 或 ``None``（不写）
        """

    def on_calendar_asof(self, ctx: "TagContext") -> TagCalendarAsOfResult:
        """可选横截面钩子；默认空（Executor 改走 per-entity ``calculate_tag``）。"""
        return TagCalendarAsOfResult(
            as_of_date=str(ctx.data.now or ""),
            entity_tags={},
            session_state={},
        )


__all__ = ["TagHooks"]
