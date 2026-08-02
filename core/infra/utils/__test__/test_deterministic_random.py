"""deterministic_random 单元测试。"""

from __future__ import annotations

import unittest
from core.infra.utils import Utils

class TestDeterministicUnitFloat(unittest.TestCase):
    def test_same_keys_same_value(self):
        a = Utils.math.deterministic_unit_float("000001.SZ", "20240102", 42)
        b = Utils.math.deterministic_unit_float("000001.SZ", "20240102", 42)
        self.assertEqual(a, b)

    def test_different_seed_different_value(self):
        a = Utils.math.deterministic_unit_float("000001.SZ", "20240102", 42)
        b = Utils.math.deterministic_unit_float("000001.SZ", "20240102", 7)
        self.assertNotEqual(a, b)

    def test_range_unit_interval(self):
        value = Utils.math.deterministic_unit_float("probe", "20240614", 1)
        self.assertGreaterEqual(value, 0.0)
        self.assertLess(value, 1.0)


if __name__ == "__main__":
    unittest.main()
