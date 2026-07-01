#!/usr/bin/env python3
"""calendar_slice 内存 budget（auto，与 BacktestEngine dispatch 同源）。"""

from __future__ import annotations

from core.infra.machine_capacity import MachineInfo
from core.modules.strategy.engines.simulator.enumerator.calendar_sliced.runtime.worker_profile import (
    profile_enumerator_dispatch_config,
)


def resolve_calendar_slice_memory_budget_mb() -> float:
    """worker 可用内存预算 MB；用户不可配置。"""
    perf = dict(profile_enumerator_dispatch_config())
    perf.setdefault("memory_budget_mb", "auto")
    perf.setdefault("dispatch_memory_budget_mb", "auto")
    budget_mb, _floor = MachineInfo.resolve_memory_budget(perf)
    return float(budget_mb)


__all__ = ["resolve_calendar_slice_memory_budget_mb"]
