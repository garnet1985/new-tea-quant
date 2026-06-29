#!/usr/bin/env python3
"""calendar_slice 内存 budget（auto，与 BacktestEngine dispatch 同源）。"""

from __future__ import annotations

from core.modules.backtest_engine.core.shared.machine_info import MachineInfo
from core.modules.backtest_engine.core.timeline_based.config import TimelineConfig
from core.modules.strategy.engines.shared.worker_settings_keys import STRATEGY_ENUM_EXECUTOR_KEY


def resolve_calendar_slice_memory_budget_mb() -> float:
    """worker 可用内存预算 MB；用户不可配置。"""
    perf = dict(TimelineConfig.resolve_dispatch_performance(STRATEGY_ENUM_EXECUTOR_KEY))
    perf.setdefault("memory_budget_mb", "auto")
    perf.setdefault("dispatch_memory_budget_mb", "auto")
    budget_mb, _floor = MachineInfo.resolve_memory_budget(perf)
    return float(budget_mb)


__all__ = ["resolve_calendar_slice_memory_budget_mb"]
