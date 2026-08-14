#!/usr/bin/env python3
"""对齐根目录 API.md 的契约测试。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pytest

from core.infra.utils import Utils
from core.infra.utils.contracts import PERIOD_DAY, PERIOD_MONTH

pytestmark = pytest.mark.force_run


class TestUtilsApi(unittest.TestCase):
    def test_facade_export(self):
        import core.infra.utils as pkg

        self.assertEqual(pkg.__all__, ["Utils"])
        self.assertTrue(hasattr(Utils, "date"))
        self.assertTrue(hasattr(Utils, "types"))
        self.assertTrue(hasattr(Utils, "io"))
        self.assertTrue(hasattr(Utils, "math"))
        self.assertTrue(hasattr(Utils, "markdown"))

    def test_markdown_template_fill(self):
        mgr = Utils.markdown.from_text("t={{:wall_clock_seconds}}")
        mgr.fill("wall_clock_seconds", "3s")
        self.assertEqual(mgr.render(), "t=3s")

    def test_date_today_and_normalize(self):
        today = Utils.date.today()
        self.assertEqual(len(today), 8)
        self.assertEqual(Utils.date.normalize_str("2024-01-15"), "20240115")

    def test_types_is_dict_and_deep_merge(self):
        self.assertTrue(Utils.types.is_dict({"a": 1}))
        merged = Utils.types.deep_merge({"a": 1, "b": {"c": 2}}, {"b": {"d": 3}})
        self.assertEqual(merged["b"]["c"], 2)
        self.assertEqual(merged["b"]["d"], 3)

    def test_io_csv_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "t.csv"
            Utils.io.write_dicts_to_csv(path, [{"a": 1, "b": 2}])
            rows = Utils.io.read_csv_to_dicts(path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["a"], "1")

    def test_math_deterministic(self):
        a = Utils.math.deterministic_unit_float("x", 1)
        b = Utils.math.deterministic_unit_float("x", 1)
        self.assertEqual(a, b)
        self.assertGreaterEqual(a, 0.0)
        self.assertLess(a, 1.0)

    def test_contracts_period(self):
        self.assertEqual(PERIOD_DAY, "day")
        self.assertEqual(PERIOD_MONTH, "month")
        self.assertEqual(Utils.date.PERIOD_DAY, PERIOD_DAY)


if __name__ == "__main__":
    unittest.main()
