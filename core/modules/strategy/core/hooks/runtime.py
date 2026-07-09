"""StrategyHooks 加载与按阶段调用。"""
from __future__ import annotations

import logging
from typing import Any, Optional

from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import (
    StrategySettings,
)
from core.modules.strategy.core.engines.shared.data_classes import CalendarAsOfResult
from core.modules.strategy.core.hooks.context import DataContext
from core.modules.strategy.core.services.discovery.worker_loader import StrategyWorkerLoader

from .base import StrategyHooks

logger = logging.getLogger(__name__)


class StrategyHookRuntime:
    """加载 hooks 类并按阶段调用；主进程与子进程共用。"""

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
    ) -> StrategyHookRuntime:
        hooks_cls = StrategyWorkerLoader.import_hooks_class(
            worker_module_path=worker_module_path,
            worker_class_name=worker_class_name,
            worker_file_path=worker_file_path,
        )
        return cls(hooks_cls(), strategy_name=strategy_name, settings=settings)

    @classmethod
    def from_job_payload(
        cls,
        job_payload: dict[str, Any],
        *,
        settings: Optional[StrategySettings] = None,
    ) -> StrategyHookRuntime:
        resolved_settings = settings or StrategySettings(raw_settings=dict(job_payload["settings"]))
        resolved_settings.apply_defaults()
        return cls.from_worker_ref(
            strategy_name=str(job_payload["strategy_name"]),
            settings=resolved_settings,
            worker_module_path=str(job_payload["worker_module_path"]),
            worker_class_name=str(job_payload["worker_class_name"]),
            worker_file_path=str(job_payload.get("worker_file_path") or ""),
        )

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
