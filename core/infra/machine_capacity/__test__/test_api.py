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
        self.assertTrue(hasattr(MachineInfo, "types"))

    def test_types_machine_capacity(self) -> None:
        self.assertIs(MachineInfo.types.MachineCapacity, MachineCapacity)

    def test_get_capacity_explicit_budget(self) -> None:
        self.assertGreaterEqual(MachineInfo.get_cpu_count(), 1)
        self.assertEqual(MachineInfo.get_cpu_count(), mp.cpu_count() or 1)
        cap = MachineInfo.get_capacity(
            {
                "reserve_cores": 1,
                "memory_budget_mb": 512,
                "memory_floor_mb": 100,
            }
        )
        self.assertIsInstance(cap, MachineCapacity)
        self.assertEqual(cap.memory_budget_mb, 512.0)
        self.assertEqual(cap.memory_floor_mb, 100.0)
        self.assertEqual(cap.reserve_cores, 1)
        self.assertEqual(
            MachineInfo.get_available_workers(cap),
            max(1, cap.cpu_count - 1),
        )

    def test_parse_max_parallel_jobs_cap(self) -> None:
        self.assertIsNone(MachineInfo.parse_max_parallel_jobs_cap(None))
        self.assertIsNone(MachineInfo.parse_max_parallel_jobs_cap("auto"))
        self.assertEqual(MachineInfo.parse_max_parallel_jobs_cap(4), 4)


if __name__ == "__main__":
    unittest.main()
