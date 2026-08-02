"""对齐根目录 API.md 的契约测试。"""

from __future__ import annotations

import unittest

import pytest

pytestmark = pytest.mark.force_run


class TestDbApi(unittest.TestCase):
    def test_facade_exported_only(self) -> None:
        import core.infra.db as pkg
        from core.infra.db import Db

        self.assertEqual(pkg.__all__, ["Db"])
        self.assertFalse(hasattr(pkg, "DatabaseManager"))
        self.assertFalse(hasattr(pkg, "create_engine"))
        self.assertFalse(hasattr(pkg, "build_engine_meta"))
        for name in ("manager", "migration", "engine", "duckdb", "sql", "rows"):
            self.assertTrue(hasattr(Db, name), name)

    def test_manager_namespace(self) -> None:
        from core.infra.db import Db

        self.assertTrue(callable(Db.manager.get_default))
        self.assertTrue(callable(Db.manager.create))
        self.assertTrue(callable(Db.manager.set_default))
        self.assertTrue(callable(Db.manager.reset_default))

    def test_migration_namespace(self) -> None:
        from core.infra.db import Db

        self.assertTrue(callable(Db.migration.default_snapshot_path))
        self.assertTrue(callable(Db.migration.build_plan))
        self.assertTrue(callable(Db.migration.run))
        self.assertTrue(callable(Db.migration.apply))

    def test_engine_namespace(self) -> None:
        from core.infra.db import Db
        from core.infra.db.contracts import EngineConfigMeta

        self.assertTrue(callable(Db.engine.build_meta))
        self.assertTrue(callable(Db.engine.create))
        meta = Db.engine.build_meta(
            {
                "database_type": "mysql",
                "mysql": {
                    "host": "127.0.0.1",
                    "port": 3306,
                    "database": "d",
                    "user": "u",
                    "password": "p",
                },
            }
        )
        self.assertIsInstance(meta, EngineConfigMeta)
        eng = Db.engine.create(meta)
        self.assertEqual(type(eng).__name__, "MysqlEngine")

    def test_duckdb_namespaces(self) -> None:
        from core.infra.db import Db

        self.assertTrue(callable(Db.duckdb.resolve_db_path))
        self.assertTrue(callable(Db.duckdb.overlay_domain_paths))
        overlay = Db.duckdb.overlay_domain_paths(
            data="/tmp/perf_test_tmp.duckdb",
            tag="/tmp/perf_test_tmp_tag.duckdb",
            strategy="/tmp/perf_test_tmp_strategy.duckdb",
        )
        self.assertEqual(overlay.get("database_type"), "duckdb")
        domains = overlay["duckdb"]["domains"]
        self.assertEqual(domains["data"]["db_path"], "/tmp/perf_test_tmp.duckdb")
        wp = Db.duckdb.worker_pool
        for name in (
            "is_backend",
            "should_apply",
            "prepare_main",
            "restore_after",
            "maybe_scope",
            "main_process",
            "recover_after_interrupt",
            "ensure_data_manager_restored",
            "wait_pool_children_done",
            "wait_for_main_end",
            "is_main_active",
            "connect_domains",
            "database_config_read_only",
            "release_worker_db_handles",
            "release_all_main_handles",
        ):
            self.assertTrue(callable(getattr(wp, name)), name)
        wal = Db.duckdb.wal
        for name in (
            "should_checkpoint_after_batch",
            "should_checkpoint_after_persist",
            "should_checkpoint_on_sigint",
            "should_checkpoint_after_tag_run",
            "checkpoint_engine",
            "install_sigint_checkpoint_handler",
        ):
            self.assertTrue(callable(getattr(wal, name)), name)
        self.assertFalse(hasattr(Db.duckdb, "process_pool_module"))

    def test_sql_and_rows_namespaces(self) -> None:
        from core.infra.db import Db

        self.assertTrue(callable(Db.sql.qualify_table_name))
        self.assertTrue(callable(Db.rows.clean_nan_in_list))
        q = Db.sql.qualify_table_name(
            {"database_type": "postgresql", "postgresql": {"pgsql_schema": "public"}},
            "t_stock",
        )
        self.assertEqual(q, "public.t_stock")
        cleaned = Db.rows.clean_nan_in_list([{"a": float("nan")}])
        self.assertEqual(len(cleaned), 1)

    def test_contracts_symbols(self) -> None:
        from core.infra.db import contracts

        for name in (
            "DatabaseManager",
            "SchemaManager",
            "DbBaseModel",
            "Field",
            "StorageRegistry",
            "STORAGE_DOMAINS",
            "BatchOperation",
            "BatchWriteQueue",
            "EngineConfigMeta",
            "DbEngineAbc",
            "DbTableAbc",
        ):
            self.assertTrue(hasattr(contracts, name), name)
        self.assertFalse(hasattr(contracts, "create_engine"))
        self.assertFalse(hasattr(contracts, "build_engine_meta"))


if __name__ == "__main__":
    unittest.main()
