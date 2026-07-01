#!/usr/bin/env python3
"""Invoke user ``StrategyHooks`` with normalized context."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.types import (
    CalendarAsOfResult,
)

from .base import StrategyHooks
from .types import StrategyHookContext

logger = logging.getLogger(__name__)


class StrategyHookRuntime:
    """加载 hooks 类并按阶段调用；主进程与子进程共用。"""

    def __init__(
        self,
        hooks: StrategyHooks,
        *,
        strategy_name: str,
        settings: StrategySettingsView,
    ) -> None:
        self.hooks = hooks
        self.strategy_name = strategy_name
        self.settings = settings

    @classmethod
    def from_worker_ref(
        cls,
        *,
        strategy_name: str,
        settings: StrategySettingsView,
        worker_module_path: str,
        worker_class_name: str,
        worker_file_path: str = "",
    ) -> StrategyHookRuntime:
        from core.modules.strategy.services.discovery.worker_loader import import_hooks_class

        hooks_cls = import_hooks_class(
            worker_module_path=worker_module_path,
            worker_class_name=worker_class_name,
            worker_file_path=worker_file_path,
        )
        return cls(hooks_cls(), strategy_name=strategy_name, settings=settings)

    @classmethod
    def from_job_payload(
        cls,
        job_payload: Dict[str, Any],
        *,
        settings: Optional[StrategySettingsView] = None,
    ) -> StrategyHookRuntime:
        resolved_settings = settings or StrategySettingsView.from_dict(job_payload["settings"])
        return cls.from_worker_ref(
            strategy_name=str(job_payload["strategy_name"]),
            settings=resolved_settings,
            worker_module_path=str(job_payload.get("worker_module_path") or ""),
            worker_class_name=str(job_payload.get("worker_class_name") or ""),
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

    def call(self, method: str, ctx: StrategyHookContext) -> Any:
        hook = getattr(self.hooks, method, None)
        if not callable(hook):
            raise AttributeError(f"StrategyHooks has no method {method!r}")
        try:
            if method == "on_calendar_asof":
                return self._normalize_calendar_asof_result(hook(ctx))
            return hook(ctx)
        except Exception as exc:
            logger.error(
                "Strategy hook failed: strategy=%s method=%s error=%s",
                self.strategy_name,
                method,
                exc,
                exc_info=True,
            )
            raise

    def call_if_overridden(self, method: str, ctx: StrategyHookContext) -> Any:
        if not self.is_overridden(method):
            return None
        return self.call(method, ctx)

    @staticmethod
    def _normalize_calendar_asof_result(raw: Any) -> CalendarAsOfResult:
        if isinstance(raw, CalendarAsOfResult):
            return raw
        if isinstance(raw, dict):
            return CalendarAsOfResult(
                selected_stock_ids=list(raw.get("selected_stock_ids") or []),
                stock_overrides=dict(raw.get("stock_overrides") or {}),
                carry=dict(raw.get("carry") or {}),
            )
        if isinstance(raw, (list, tuple)):
            return CalendarAsOfResult(selected_stock_ids=[str(x) for x in raw])
        raise TypeError("on_calendar_asof 须返回 CalendarAsOfResult、dict 或 stock_id 列表")


__all__ = ["StrategyHookRuntime"]
