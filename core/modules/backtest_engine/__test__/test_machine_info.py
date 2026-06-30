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


def test_worker_pool_budget_does_not_subtract_floor_twice() -> None:
    from core.modules.backtest_engine.core.shared.machine_info import MachineCapacity

    capacity = MachineCapacity(
        cpu_count=10,
        memory_budget_mb=3500.0,
        memory_floor_mb=3600.0,
        reserve_cores=2,
    )
    assert MachineInfo.worker_pool_budget_mb(capacity) == 3500.0


def test_resolve_max_workers_auto() -> None:
    from core.modules.backtest_engine.core.timeline_based.probe import WorkerProbe

    workers = WorkerProbe.resolve("auto", reserve_cores=1, cap=None)
    assert workers >= 1
