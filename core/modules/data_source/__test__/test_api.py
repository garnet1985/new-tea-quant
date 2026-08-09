#!/usr/bin/env python3
"""DataSourceManager facade API contract tests（对齐 API.md）。"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.force_run


class TestDataSourceApi(unittest.TestCase):
    def test_facade_export(self):
        import core.modules.data_source as pkg

        from core.modules.data_source import DataSourceManager

        self.assertEqual(pkg.__all__, ["DataSourceManager"])
        self.assertTrue(callable(DataSourceManager))

    def test_public_methods_present(self):
        from core.modules.data_source import DataSourceManager

        mgr = DataSourceManager(is_verbose=False)
        for name in (
            "renew",
            "resolve_renew_target",
            "list_renew_targets",
            "format_renew_targets_help",
            "execute",
        ):
            self.assertTrue(callable(getattr(mgr, name)), name)
        self.assertTrue(callable(DataSourceManager.format_renew_targets_help))
        self.assertTrue(callable(DataSourceManager.get_data_end_meta))
        self.assertTrue(callable(DataSourceManager.resolve_freshness_end_date))

    def test_resolve_renew_target_empty_raises(self):
        from core.modules.data_source import DataSourceManager

        mgr = DataSourceManager(is_verbose=False)
        with self.assertRaises(ValueError):
            mgr.resolve_renew_target("")

    def test_renew_delegates_to_execute(self):
        from core.modules.data_source import DataSourceManager

        mgr = DataSourceManager(is_verbose=False)
        with patch.object(mgr, "resolve_renew_target", return_value="stock_klines") as resolve:
            with patch.object(mgr, "execute") as execute:
                mgr.renew(table_name="sys_stock_klines", force=True)
        resolve.assert_called_once_with("sys_stock_klines")
        execute.assert_called_once_with(sources=("stock_klines",), force=True)

    def test_renew_all_delegates_to_execute(self):
        from core.modules.data_source import DataSourceManager

        mgr = DataSourceManager(is_verbose=False)
        with patch.object(mgr, "execute") as execute:
            mgr.renew(table_name=None, force=False)
        execute.assert_called_once_with(sources=None, force=False)

    def test_list_renew_targets_shape(self):
        from core.modules.data_source import DataSourceManager
        from core.modules.data_source.core.data_class.handler_mapping import HandlerMapping

        mgr = DataSourceManager(is_verbose=False)
        mapping = HandlerMapping(
            {"stock_klines": {"is_enabled": True, "handler": "StockKlinesHandler"}}
        )
        cfg = MagicMock()
        cfg.get_table_name.return_value = "sys_stock_klines"
        with patch.object(mgr, "_flush_cache"):
            with patch.object(mgr, "_discover_mappings", return_value=mapping):
                with patch.object(mgr, "_discover_config", return_value=cfg):
                    rows = mgr.list_renew_targets()
        self.assertEqual(rows, [{"source": "stock_klines", "table": "sys_stock_klines"}])

    def test_contracts_symbols(self):
        from core.modules.data_source.contracts import (
            ApiJob,
            ApiJobBundle,
            BaseHandler,
            BaseProvider,
        )

        self.assertIsNotNone(BaseProvider)
        self.assertIsNotNone(BaseHandler)
        self.assertIsNotNone(ApiJob)
        self.assertIsNotNone(ApiJobBundle)


if __name__ == "__main__":
    unittest.main()
