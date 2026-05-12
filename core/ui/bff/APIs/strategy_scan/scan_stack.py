"""Defer strategy scanner imports until first scan API use."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

_stack: Optional[SimpleNamespace] = None


def get_strategy_scan_stack() -> SimpleNamespace:
    global _stack
    if _stack is not None:
        return _stack
    from core.modules.strategy.launcher.scanner_run import (
        get_scan_progress,
        get_scan_readiness,
        trigger_strategy_scan_run,
    )

    _stack = SimpleNamespace(
        get_scan_progress=get_scan_progress,
        get_scan_readiness=get_scan_readiness,
        trigger_strategy_scan_run=trigger_strategy_scan_run,
    )
    return _stack
