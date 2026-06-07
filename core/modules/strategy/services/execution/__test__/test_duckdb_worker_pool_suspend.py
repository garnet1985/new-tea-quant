"""DuckDB 主进程 suspend（infra process_pool_scope）。"""
from unittest.mock import MagicMock, patch

from core.infra.db.engines.duckdb import process_pool_scope as scope


def test_duckdb_worker_pool_suspend_reentrant():
    dm = MagicMock()
    dm.db = MagicMock(config={"database_type": "duckdb"})

    calls: list[str] = []

    def fake_prepare(data_mgr):
        calls.append("prepare")

    def fake_restore():
        calls.append("restore")

    def fake_resume(data_mgr, **kwargs):
        calls.append("resume")

    def fake_wait(**kwargs):
        calls.append("wait")

    with patch.object(scope, "is_duckdb_backend", return_value=True), patch.object(
        scope, "prepare_main_for_worker_pool",
        side_effect=fake_prepare,
    ), patch.object(
        scope, "restore_after_worker_pool",
        side_effect=fake_restore,
    ), patch.object(
        scope, "ensure_data_manager_restored",
        side_effect=fake_resume,
    ), patch.object(
        scope, "wait_pool_children_done",
        side_effect=fake_wait,
    ):
        scope._MAIN_SUSPEND_DEPTH = 0
        with scope.duckdb_worker_pool_main_process(dm):
            with scope.duckdb_worker_pool_main_process(dm):
                pass

    assert calls == ["prepare", "wait", "restore", "resume"]
    assert scope._MAIN_SUSPEND_DEPTH == 0


def test_duckdb_worker_pool_skipped_for_mysql():
    dm = MagicMock()
    with patch.object(scope, "is_duckdb_backend", return_value=False), patch.object(
        scope, "prepare_main_for_worker_pool",
    ) as prepare:
        with scope.duckdb_worker_pool_main_process(dm):
            pass
        prepare.assert_not_called()


def test_prepare_main_closes_orphan_database_manager():
    from core.infra.db import DatabaseManager
    from core.modules.data_manager import DataManager

    db = MagicMock()
    db.close = MagicMock()
    DatabaseManager._default_instance = db
    DataManager._instance = None

    try:
        scope.prepare_main_for_worker_pool(None)
        assert DatabaseManager._default_instance is None
        assert db.close.call_count >= 1
        assert DataManager.get_instance() is None
    finally:
        DatabaseManager._default_instance = None
        DataManager._instance = None
        DatabaseManager._auto_init_enabled = True


def test_resolve_data_manager_does_not_create_by_default():
    from core.modules.data_manager import DataManager

    DataManager._instance = None
    try:
        assert scope.resolve_data_manager(None) is None
        with patch.object(DataManager, "__init__", wraps=DataManager.__init__) as init:
            scope.resolve_data_manager(None)
            init.assert_not_called()
    finally:
        DataManager._instance = None
