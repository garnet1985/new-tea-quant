#!/usr/bin/env python3
"""DataManager facade API contract tests."""

from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.force_run


class TestDataManagerApi(unittest.TestCase):
    def test_facade_export(self):
        import core.modules.data_manager as pkg

        from core.modules.data_manager import DataManager

        self.assertEqual(pkg.__all__, ["DataManager"])
        self.assertTrue(callable(DataManager))

    def test_calendar_property_after_init(self):
        from core.modules.data_manager import DataManager

        dm = DataManager(force_new=True, is_verbose=False)
        self.assertTrue(hasattr(dm, "calendar"))
        self.assertTrue(hasattr(dm, "stock"))

    def test_contracts_base_table_names(self):
        from core.modules.data_manager.contracts import BaseTableNames

        self.assertEqual(BaseTableNames.stock_list.value, "stock_list")


if __name__ == "__main__":
    unittest.main()
