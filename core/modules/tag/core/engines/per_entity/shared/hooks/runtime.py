"""TagHooks 加载与按阶段调用。

消费者: TagSliceJobExecutor

本文件:
- TagHookRuntime: 从 tag_info 实例化 hooks 并分派调用
  边界: 负责 hooks 生命周期与统一调用；不负责数据装载或落盘
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple, Union

from core.modules.tag.core.engines.per_entity.shared.data_class.calendar_as_of import (
    TagCalendarAsOfResult,
)
from core.modules.tag.core.engines.per_entity.shared.hooks.hook_params import TagContext
from core.modules.tag.core.engines.per_entity.shared.hooks.tag_hooks import TagHooks
from core.modules.tag.core.engines.per_entity.shared.tag_settings.tag_settings import TagSettings
from core.modules.tag.core.services.discovery.hooks_loader import TagHooksLoader

logger = logging.getLogger(__name__)


class TagHookRuntime:
    """加载 hooks 并统一调用。"""

    def __init__(
        self,
        hooks: TagHooks,
        *,
        tag_name: str,
        settings: TagSettings,
    ) -> None:
        self.hooks = hooks
        self.tag_name = tag_name
        self.settings = settings

    @classmethod
    def from_hooks_ref(
        cls,
        *,
        tag_name: str,
        settings: TagSettings,
        hooks_module_path: str,
        hooks_class_name: str,
        hooks_file_path: str = "",
    ) -> "TagHookRuntime":
        hooks_cls = TagHooksLoader.import_hooks_class(
            hooks_module_path=hooks_module_path,
            hooks_class_name=hooks_class_name,
            hooks_file_path=hooks_file_path,
        )
        return cls(hooks_cls(), tag_name=tag_name, settings=settings)

    @classmethod
    def from_tag_info(
        cls,
        tag_info: Union[Dict[str, Any], Any],
        settings: TagSettings,
    ) -> Tuple[Optional["TagHookRuntime"], Optional[Dict[str, Any]]]:
        """从 payload.tag_info 或 EnabledTagInfo 加载；失败返回 (None, error_dict)。"""
        if isinstance(tag_info, dict):
            module_path = str(tag_info.get("hooks_module_path") or "").strip()
            class_name = str(tag_info.get("hooks_class_name") or "").strip()
            if not class_name:
                hooks_cls = tag_info.get("hooks_class")
                class_name = getattr(hooks_cls, "__name__", "") or ""
            file_path = str(tag_info.get("hooks_file_path") or "").strip()
            tag_name = str(
                tag_info.get("key")
                or tag_info.get("unique_relative_path")
                or ""
            ).strip()
        else:
            module_path = str(getattr(tag_info, "hooks_module_path", "") or "").strip()
            hooks_cls = getattr(tag_info, "hooks_class", None)
            class_name = str(getattr(tag_info, "hooks_class_name", "") or "").strip()
            if not class_name and hooks_cls is not None:
                class_name = hooks_cls.__name__
            file_path = str(
                getattr(tag_info, "hooks_file_path", None)
                or getattr(tag_info, "tag_file", "")
                or ""
            )
            tag_name = str(
                getattr(tag_info, "key", None)
                or getattr(tag_info, "unique_relative_path", "")
                or ""
            ).strip()

        if not module_path or not class_name:
            return None, {
                "success": False,
                "tag_values_count": 0,
                "error": "缺少hooks信息",
            }
        try:
            runtime = cls.from_hooks_ref(
                tag_name=tag_name,
                settings=settings,
                hooks_module_path=module_path,
                hooks_class_name=class_name,
                hooks_file_path=file_path,
            )
            return runtime, None
        except Exception as exc:
            logger.error("加载 tag hooks 失败：%s", exc, exc_info=True)
            return None, {
                "success": False,
                "tag_values_count": 0,
                "error": str(exc),
            }

    def is_overridden(self, method: str) -> bool:
        base = getattr(TagHooks, method, None)
        impl = getattr(self.hooks, method, None)
        if not callable(impl):
            return False
        if base is None:
            return True
        return getattr(impl, "__func__", impl) is not base

    def call(self, method: str, ctx: TagContext) -> Any:
        hook = getattr(self.hooks, method, None)
        if not callable(hook):
            raise AttributeError(f"TagHooks has no method {method!r}")
        try:
            result = hook(ctx)
            if method == "on_calendar_asof" and not isinstance(
                result, TagCalendarAsOfResult
            ):
                raise TypeError(
                    f"{method} 必须返回 TagCalendarAsOfResult，"
                    f"实际: {type(result).__name__}"
                )
            return result
        except Exception as exc:
            logger.error(
                "Tag hook failed: tag=%s method=%s error=%s",
                self.tag_name,
                method,
                exc,
                exc_info=True,
            )
            raise

    def call_if_overridden(self, method: str, ctx: TagContext) -> Any:
        if not self.is_overridden(method):
            return None
        return self.call(method, ctx)


__all__ = ["TagHookRuntime"]
