"""对齐根目录 API.md 的契约测试。"""

from __future__ import annotations

import multiprocessing as mp
import unittest

import pytest

from core.infra.machine_capacity import MachineInfo
from core.infra.machine_capacity.contracts import MachineCapacity

pytestmark = pytest.mark.force_run


class TestMachineCapacityApi(unittest.TestCase):
    def test_facade_exported_only(self) -> None:
        import core.infra.machine_capacity as pkg

        self.assertEqual(pkg.__all__, ["MachineInfo"])
        self.assertFalse(hasattr(pkg, "MachineCapacity"))

    def test_contracts_machine_capacity(self) -> None:
        cap = MachineCapacity(
            cpu_count=4,
            memory_budget_mb=1024.0,
            memory_floor_mb=256.0,
            reserve_cores=1,
        )
        self.assertEqual(MachineInfo.get_available_workers(cap), 3)

    def test_get_capacity_and_cpu(self) -> None:
        self.assertGreaterEqual(MachineInfo.get_cpu_count(), 1)
        self.assertEqual(MachineInfo.get_cpu_count(), mp.cpu_count() or 1)
        cap = MachineInfo.get_capacity(
            {"reserve_cores": 1, "memory_budget_mb": 512, "memory_floor_mb": 100}
        )
        self.assertIsInstance(cap, MachineCapacity)
        self.assertEqual(cap.memory_budget_mb, 512.0)

    def test_parse_max_parallel_jobs_cap(self) -> None:
        self.assertIsNone(MachineInfo.parse_max_parallel_jobs_cap(None))
        self.assertEqual(MachineInfo.parse_max_parallel_jobs_cap(4), 4)


if __name__ == "__main__":
    unittest.main()
