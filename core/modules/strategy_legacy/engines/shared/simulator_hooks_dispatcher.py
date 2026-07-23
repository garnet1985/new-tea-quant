#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import logging

from core.modules.strategy.engines.shared.helpers.strategy_runtime import (
    load_strategy_settings_view,
    resolve_hooks_class,
)
from core.modules.strategy.hooks import StrategyHookContext, StrategyHookRuntime

logger = logging.getLogger(__name__)


@dataclass
class SimulatorHooksDispatcher:
    strategy_name: str

    def __post_init__(self) -> None:
        self._runtime: Optional[StrategyHookRuntime] = None

    def _get_runtime(self) -> Optional[StrategyHookRuntime]:
        if self._runtime is not None:
            return self._runtime
        try:
            settings = load_strategy_settings_view(self.strategy_name)
            hooks_cls = resolve_hooks_class(self.strategy_name)
            self._runtime = StrategyHookRuntime(
                hooks_cls(),
                strategy_name=self.strategy_name,
                settings=settings,
            )
        except Exception as exc:
            logger.warning("[SimulatorHooksDispatcher] init hooks failed: %s", exc)
            self._runtime = None
        return self._runtime

    def call_hook(self, hook_name: str, ctx: StrategyHookContext) -> Any:
        runtime = self._get_runtime()
        if runtime is None:
            return None
        if not runtime.is_overridden(hook_name):
            if hook_name == "on_price_factor_after_process_stock":
                pf = ctx.price_factor
                if pf is not None and pf.stock_summary is not None:
                    return pf.stock_summary
            if hook_name == "on_price_factor_opportunity_trigger":
                pf = ctx.price_factor
                if pf is not None and pf.opportunity_row is not None:
                    return pf.opportunity_row
            if hook_name == "on_price_factor_target_hit":
                pf = ctx.price_factor
                if pf is not None and pf.target_row is not None:
                    return pf.target_row
            return None
        try:
            return runtime.call(hook_name, ctx)
        except Exception as exc:
            logger.warning("[SimulatorHooksDispatcher] hook failed %s: %s", hook_name, exc)
            return None


__all__ = ["SimulatorHooksDispatcher"]
