"""StrategyHooks 加载与按阶段调用（主进程 / worker 热路径入口）。

本文件:
- StrategyHookRuntime: 从 worker_ref / strategy_info 实例化 hooks 并分派调用
  边界: 负责 hooks 生命周期与统一调用；不负责 contract 加载或报告落盘
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple, Union

from core.modules.strategy.core.engines.enumerator.slice_based.types import (
    CalendarAsOfResult,
)
from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.hooks.context import DataContext
from core.modules.strategy.core.services.discovery.worker_loader import StrategyWorkerLoader

from .base import StrategyHooks

logger = logging.getLogger(__name__)


class StrategyHookRuntime:
    """加载 hooks 并统一调用；主进程 / worker / timeline 共用。"""

    def __init__(
        self,
        hooks: StrategyHooks,
        *,
        strategy_name: str,
        settings: StrategySettings,
    ) -> None:
        self.hooks = hooks
        self.strategy_name = strategy_name
        self.settings = settings

    @classmethod
    def from_worker_ref(
        cls,
        *,
        strategy_name: str,
        settings: StrategySettings,
        worker_module_path: str,
        worker_class_name: str,
        worker_file_path: str = "",
    ) -> "StrategyHookRuntime":
        hooks_cls = StrategyWorkerLoader.import_hooks_class(
            worker_module_path=worker_module_path,
            worker_class_name=worker_class_name,
            worker_file_path=worker_file_path,
        )
        return cls(hooks_cls(), strategy_name=strategy_name, settings=settings)

    @classmethod
    def from_strategy_info(
        cls,
        strategy_info: Union[Dict[str, Any], Any],
        settings: StrategySettings,
    ) -> Tuple[Optional["StrategyHookRuntime"], Optional[Dict[str, Any]]]:
        """从 payload.strategy_info 或 EnabledStrategyInfo 加载；失败返回 (None, error_dict)。"""
        if isinstance(strategy_info, dict):
            module_path = str(strategy_info.get("hooks_module_path") or "").strip()
            class_name = str(strategy_info.get("hooks_class_name") or "").strip()
            if not class_name:
                hooks_cls = strategy_info.get("hooks_class")
                class_name = getattr(hooks_cls, "__name__", "") or ""
            file_path = str(strategy_info.get("hooks_file_path") or "").strip()
            strategy_name = str(
                strategy_info.get("key")
                or strategy_info.get("unique_relative_path")
                or ""
            ).strip()
        else:
            module_path = str(getattr(strategy_info, "hooks_module_path", "") or "").strip()
            hooks_cls = getattr(strategy_info, "hooks_class", None)
            class_name = hooks_cls.__name__ if hooks_cls is not None else ""
            file_path = str(getattr(strategy_info, "strategy_file", "") or "")
            strategy_name = str(
                getattr(strategy_info, "key", None)
                or getattr(strategy_info, "unique_relative_path", "")
                or ""
            ).strip()

        if not module_path or not class_name:
            return None, {
                "success": False,
                "opportunities_count": 0,
                "error": "缺少hooks信息",
            }
        try:
            runtime = cls.from_worker_ref(
                strategy_name=strategy_name,
                settings=settings,
                worker_module_path=module_path,
                worker_class_name=class_name,
                worker_file_path=file_path,
            )
            return runtime, None
        except Exception as exc:
            logger.error("加载hooks类失败：%s", exc, exc_info=True)
            return None, {
                "success": False,
                "opportunities_count": 0,
                "error": str(exc),
            }

    def is_overridden(self, method: str) -> bool:
        base = getattr(StrategyHooks, method, None)
        impl = getattr(self.hooks, method, None)
        if not callable(impl):
            return False
        if base is None:
            return True
        return getattr(impl, "__func__", impl) is not base

    def call(self, method: str, ctx: DataContext) -> Any:
        hook = getattr(self.hooks, method, None)
        if not callable(hook):
            raise AttributeError(f"StrategyHooks has no method {method!r}")
        try:
            result = hook(ctx)
            if method == "on_calendar_asof" and not isinstance(result, CalendarAsOfResult):
                raise TypeError(
                    f"{method} 必须返回 CalendarAsOfResult，实际: {type(result).__name__}"
                )
            return result
        except Exception as exc:
            logger.error(
                "Strategy hook failed: strategy=%s method=%s error=%s",
                self.strategy_name,
                method,
                exc,
                exc_info=True,
            )
            raise

    def call_if_overridden(self, method: str, ctx: DataContext) -> Any:
        if not self.is_overridden(method):
            return None
        return self.call(method, ctx)


__all__ = ["StrategyHookRuntime"]
