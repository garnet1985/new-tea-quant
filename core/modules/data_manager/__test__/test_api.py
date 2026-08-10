#!/usr/bin/env python3
"""DataManager facade API contract tests（对齐 API.md）。"""

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

    def test_domain_properties_after_init(self):
        from core.modules.data_manager import DataManager

        dm = DataManager(force_new=True, is_verbose=False)
        for name in (
            "stock",
            "macro",
            "calendar",
            "index",
            "db_cache",
            "backup_restore",
            "service",
        ):
            self.assertTrue(hasattr(dm, name), name)
            getattr(dm, name)

    def test_get_table_and_physical_name(self):
        from core.modules.data_manager import DataManager
        from core.modules.data_manager.contracts import BaseTableNames

        dm = DataManager(force_new=True, is_verbose=False)
        model = dm.get_table(BaseTableNames.STOCK_LIST.value)
        self.assertIsNotNone(model)
        physical = dm.get_physical_table_name(BaseTableNames.STOCK_LIST.value)
        self.assertTrue(str(physical))

    def test_normalize_delist_date(self):
        from core.modules.data_manager import DataManager

        self.assertIsNone(DataManager.normalize_delist_date("0"))
        self.assertIsNone(DataManager.normalize_delist_date(0.0))
        self.assertEqual(DataManager.normalize_delist_date("20200101"), "20200101")

    def test_register_calendar_real_world_fetcher(self):
        from core.modules.data_manager import DataManager
        from core.modules.data_manager.core.data_services.calendar.calendar_service import (
            CalendarService,
        )

        def _fetcher():
            return ("20250520", "test")

        DataManager.register_calendar_real_world_fetcher(_fetcher)
        self.assertIs(CalendarService._real_world_fetcher, _fetcher)
        DataManager.register_calendar_real_world_fetcher(None)

    def test_attach_data_service(self):
        from core.modules.data_manager import DataManager

        dm = DataManager(force_new=True, is_verbose=False)
        svc = dm.attach_data_service()
        self.assertIsNotNone(svc)
        self.assertIs(dm.service, svc)
        self.assertTrue(hasattr(svc, "stock"))

    def test_contracts_base_table_names(self):
        from core.modules.data_manager.contracts import BaseTableNames

        self.assertEqual(BaseTableNames.STOCK_LIST.value, "sys_stock_list")
        self.assertEqual(BaseTableNames.STOCK_KLINES.value, "sys_stock_klines")
        self.assertEqual(
            BaseTableNames.ADJ_FACTOR_EVENTS.value, "sys_adj_factor_events"
        )

    def test_singleton_helpers(self):
        from core.modules.data_manager import DataManager

        DataManager.reset_instance()
        a = DataManager(is_verbose=False)
        self.assertIs(DataManager.get_instance(), a)
        b = DataManager(is_verbose=False)
        self.assertIs(b, a)
        DataManager.reset_instance()
        self.assertIsNone(DataManager.get_instance())

    def test_duckdb_pool_holder_resolver_and_restore_api(self):
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool
        from core.modules.data_manager import DataManager

        DataManager.ensure_duckdb_pool_holder_resolver()
        self.assertTrue(callable(DuckdbWorkerPool._holder_resolver))
        self.assertTrue(callable(DataManager.ensure_restored_after_worker_pool))
        self.assertTrue(callable(DataManager.bind_as_default_instance))


if __name__ == "__main__":
    unittest.main()
