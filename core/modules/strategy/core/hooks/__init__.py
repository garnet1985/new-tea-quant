"""Hooks exports."""

from .base import StrategyHooks

__all__ = ["StrategyHookRuntime", "StrategyHooks"]


def __getattr__(name: str):
    if name == "StrategyHookRuntime":
        from .runtime import StrategyHookRuntime

        return StrategyHookRuntime
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
