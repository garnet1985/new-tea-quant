#!/usr/bin/env python3
"""calendar_slice 内存 budget（auto，与 entity_timeline dispatch 同源）。"""

from __future__ import annotations

from core.infra.worker.dispatch_planner import resolve_memory_budget_mb
from core.modules.strategy.services.execution.enum_dispatch import (
    enumerator_dispatch_dict,
)


def resolve_calendar_slice_memory_budget_mb() -> float:
    """worker 可用内存预算 MB；用户不可配置。"""
    perf = dict(enumerator_dispatch_dict())
    perf.setdefault("memory_budget_mb", "auto")
    perf.setdefault("dispatch_memory_budget_mb", "auto")
    budget_mb, _floor = resolve_memory_budget_mb(perf)
    return float(budget_mb)


__all__ = ["resolve_calendar_slice_memory_budget_mb"]
