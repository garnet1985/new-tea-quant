#!/usr/bin/env python3
"""DataSourceManager facade API contract tests."""

from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.force_run


class TestDataSourceApi(unittest.TestCase):
    def test_facade_export(self):
        import core.modules.data_source as pkg

        from core.modules.data_source import DataSourceManager

        self.assertEqual(pkg.__all__, ["DataSourceManager"])
        self.assertTrue(callable(DataSourceManager))

    def test_renew_api(self):
        from core.modules.data_source import DataSourceManager

        mgr = DataSourceManager(is_verbose=False)
        self.assertTrue(callable(mgr.renew))
        self.assertTrue(callable(mgr.resolve_renew_target))
        self.assertTrue(callable(mgr.list_renew_targets))

    def test_contracts_symbols(self):
        from core.modules.data_source.contracts import (
            ApiJob,
            ApiJobBundle,
            BaseHandler,
            BaseProvider,
        )

        self.assertTrue(BaseProvider is not None)
        self.assertTrue(BaseHandler is not None)
        self.assertTrue(ApiJob is not None)
        self.assertTrue(ApiJobBundle is not None)


if __name__ == "__main__":
    unittest.main()
