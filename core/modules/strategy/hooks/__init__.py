#!/usr/bin/env python3
"""Strategy hooks — user extension API and runtime."""

from .base import StrategyHooks
from .context import (
    batch_context,
    calendar_asof_context,
    entity_context,
    price_factor_context,
    run_context,
    scan_context,
)
from .runtime import StrategyHookRuntime
from .types import (
    BatchScope,
    EntityScope,
    HookPhase,
    PriceFactorScope,
    RunScope,
    ScanScope,
    StrategyHookContext,
)

__all__ = [
    "BatchScope",
    "EntityScope",
    "HookPhase",
    "PriceFactorScope",
    "RunScope",
    "ScanScope",
    "StrategyHookContext",
    "StrategyHookRuntime",
    "StrategyHooks",
    "batch_context",
    "calendar_asof_context",
    "entity_context",
    "price_factor_context",
    "run_context",
    "scan_context",
]


def __getattr__(name: str):
    if name == "resolve_hooks_class":
        from core.modules.strategy.engines.shared.helpers.strategy_runtime import (
            resolve_hooks_class,
        )

        return resolve_hooks_class
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
