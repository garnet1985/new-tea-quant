"""MachineInfo 容量解析行为单测。"""
from __future__ import annotations

import pytest

from core.infra.machine_capacity import MachineInfo
from core.infra.machine_capacity.contracts import MachineCapacity

pytestmark = pytest.mark.force_run


def test_get_reserve_cores_defaults_and_clamps() -> None:
    assert MachineInfo.get_reserve_cores({}) == 1
    assert MachineInfo.get_reserve_cores({"reserve_cores": 3}) == 3
    assert MachineInfo.get_reserve_cores({"reserve_cores": "bad"}) == 1
    assert MachineInfo.get_reserve_cores({"reserve_cores": -2}) == 0


def test_resolve_memory_budget_explicit() -> None:
    budget, floor = MachineInfo.resolve_memory_budget(
        {"memory_budget_mb": 512, "memory_floor_mb": 100}
    )
    assert budget == 512.0
    assert floor == 100.0


def test_get_available_workers() -> None:
    cap = MachineCapacity(
        cpu_count=8,
        memory_budget_mb=4096.0,
        memory_floor_mb=1024.0,
        reserve_cores=2,
    )
    assert MachineInfo.get_available_workers(cap) == 6


def test_worker_pool_budget_mb() -> None:
    cap = MachineCapacity(
        cpu_count=2,
        memory_budget_mb=0.0,
        memory_floor_mb=0.0,
        reserve_cores=0,
    )
    assert MachineInfo.worker_pool_budget_mb(cap) == 1.0


def test_parse_max_parallel_jobs_cap_edges() -> None:
    assert MachineInfo.parse_max_parallel_jobs_cap(None) is None
    assert MachineInfo.parse_max_parallel_jobs_cap("") is None
    assert MachineInfo.parse_max_parallel_jobs_cap("null") is None
    assert MachineInfo.parse_max_parallel_jobs_cap("auto") is None
    assert MachineInfo.parse_max_parallel_jobs_cap("8") == 8
    assert MachineInfo.parse_max_parallel_jobs_cap(4) == 4
    assert MachineInfo.parse_max_parallel_jobs_cap(0) == 1
    assert MachineInfo.parse_max_parallel_jobs_cap("bad") is None


def test_virtual_memory_mb_shape() -> None:
    total, available = MachineInfo.virtual_memory_mb()
    if total is None:
        assert available is None
    else:
        assert available is not None
        assert total > 0
        assert available >= 0
