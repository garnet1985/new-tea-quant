"""MachineInfo auto memory / worker resolution tests."""
from __future__ import annotations

from core.modules.backtest_engine.core.shared.machine_info import MachineInfo


def test_resolve_memory_floor_auto() -> None:
    floor = MachineInfo.resolve_memory_floor({"memory_floor_mb": "auto"})
    assert floor >= 1024.0


def test_resolve_memory_budget_auto() -> None:
    budget, floor = MachineInfo.resolve_memory_budget(
        {
            "memory_budget_mb": "auto",
            "memory_floor_mb": "auto",
            "worker_memory_fraction": 0.85,
        }
    )
    assert budget >= 256.0
    assert floor >= 1024.0
    assert budget <= 16384.0


def test_resolve_max_workers_auto() -> None:
    workers = MachineInfo.resolve_max_workers(
        {"max_workers": "auto", "reserve_cores": 1},
        dispatch_jobs=100,
    )
    assert workers >= 1
