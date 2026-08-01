"""对齐根目录 API.md 的契约测试。"""

from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.force_run


class TestDbApi(unittest.TestCase):
    def test_facade_exported(self) -> None:
        import core.infra.db as pkg
        from core.infra.db import Db

        self.assertIn("Db", pkg.__all__)
        self.assertTrue(hasattr(Db, "manager"))
        self.assertTrue(hasattr(Db, "migration"))
        self.assertTrue(hasattr(Db, "duckdb"))

    def test_manager_namespace(self) -> None:
        from core.infra.db import Db
        from core.infra.db.contracts import DatabaseManager

        self.assertIs(Db.manager.DatabaseManager, DatabaseManager)
        self.assertTrue(callable(Db.manager.get_default))
        self.assertTrue(callable(Db.manager.create))
        self.assertTrue(callable(Db.manager.set_default))
        self.assertTrue(callable(Db.manager.reset_default))

    def test_migration_namespace(self) -> None:
        from core.infra.db import Db

        self.assertTrue(callable(Db.migration.build_plan))
        self.assertTrue(callable(Db.migration.run))

    def test_duckdb_namespace(self) -> None:
        from core.infra.db import Db

        mod = Db.duckdb.process_pool_module()
        self.assertTrue(hasattr(mod, "prepare_main_for_worker_pool"))
        self.assertTrue(hasattr(mod, "restore_after_worker_pool"))

    def test_contracts_symbols(self) -> None:
        from core.infra.db import contracts

        for name in (
            "DatabaseManager",
            "DbBaseModel",
            "Field",
            "StorageRegistry",
            "STORAGE_DOMAINS",
            "BatchOperation",
            "BatchWriteQueue",
        ):
            self.assertTrue(hasattr(contracts, name), name)

    def test_transitional_package_reexports(self) -> None:
        from core.infra.db import DatabaseManager, DbBaseModel, Field

        self.assertTrue(callable(DatabaseManager.get_default))
        self.assertTrue(DbBaseModel is not None)
        self.assertTrue(Field is not None)


if __name__ == "__main__":
    unittest.main()
