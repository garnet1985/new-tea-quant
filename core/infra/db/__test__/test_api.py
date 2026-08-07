"""对齐根目录 API.md 的契约测试。"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

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
        root = Path("/tmp/ntq_repo")
        snap = Db.migration.default_snapshot_path(root)
        self.assertEqual(snap.name, "pre_mirror_core_table_schemas.json")
        self.assertEqual(snap.parent.name, "cache")
        self.assertEqual(snap.parent.parent.name, "update")

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
            "install_config_overlay",
            "release_worker_db_handles",
            "release_all_main_handles",
        ):
            self.assertTrue(callable(getattr(wp, name)), name)
        self.assertEqual(wp.CONFIG_OVERLAY_ENV, "NTQ_DATABASE_CONFIG_JSON")
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

    def test_worker_pool_should_apply_behavior(self) -> None:
        from core.infra.db import Db
        from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool

        wp = Db.duckdb.worker_pool
        self.assertFalse(
            wp.should_apply(mode="off", use_process_pool=True, data_mgr=None)
        )
        self.assertFalse(
            wp.should_apply(mode="on", use_process_pool=False, data_mgr=None)
        )
        self.assertTrue(
            wp.should_apply(mode="on", use_process_pool=True, data_mgr=None)
        )
        self.assertFalse(
            wp.should_apply(mode="auto", use_process_pool=False, data_mgr=None)
        )
        with patch.object(DuckdbWorkerPool, "is_duckdb_backend", return_value=True):
            self.assertTrue(
                wp.should_apply(mode="auto", use_process_pool=True, data_mgr=object())
            )
        with patch.object(DuckdbWorkerPool, "is_duckdb_backend", return_value=False):
            self.assertFalse(
                wp.should_apply(mode="auto", use_process_pool=True, data_mgr=object())
            )

    def test_worker_pool_install_config_overlay(self) -> None:
        from core.infra.db import Db

        wp = Db.duckdb.worker_pool
        env_key = wp.CONFIG_OVERLAY_ENV
        prev = os.environ.pop(env_key, None)
        try:
            cfg = {
                "database_type": "duckdb",
                "duckdb": {
                    "domains": {
                        "data": {"db_path": "/tmp/overlay_data.duckdb"},
                    }
                },
            }
            wp.install_config_overlay(cfg)
            self.assertEqual(json.loads(os.environ[env_key])["database_type"], "duckdb")
            loaded = wp.database_config_read_only()
            self.assertTrue(
                loaded["duckdb"]["domains"]["data"].get("read_only") is True
            )
            self.assertEqual(
                loaded["duckdb"]["domains"]["data"]["db_path"],
                "/tmp/overlay_data.duckdb",
            )
        finally:
            if prev is None:
                os.environ.pop(env_key, None)
            else:
                os.environ[env_key] = prev

    def test_wal_checkpoint_defaults(self) -> None:
        from core.infra.db import Db

        wal = Db.duckdb.wal
        empty: dict = {}
        self.assertTrue(wal.should_checkpoint_after_batch(empty))
        self.assertFalse(wal.should_checkpoint_after_persist(empty))
        self.assertTrue(wal.should_checkpoint_on_sigint(empty))
        self.assertTrue(wal.should_checkpoint_after_tag_run(empty))
        explicit = {
            "duckdb": {
                "checkpoint_after_batch_save": False,
                "checkpoint_after_persist": True,
                "checkpoint_on_sigint": False,
                "checkpoint_after_tag_run": False,
            }
        }
        self.assertFalse(wal.should_checkpoint_after_batch(explicit))
        self.assertTrue(wal.should_checkpoint_after_persist(explicit))
        self.assertFalse(wal.should_checkpoint_on_sigint(explicit))
        self.assertFalse(wal.should_checkpoint_after_tag_run(explicit))

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
