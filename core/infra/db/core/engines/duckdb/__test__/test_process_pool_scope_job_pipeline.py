"""JobPipeline 与 process_pool_scope 集成判断。"""
from unittest.mock import patch

from core.infra.db.core.engines.duckdb.process_pool_scope import DuckdbWorkerPool


def test_should_apply_auto_duckdb_process():
    with patch.object(DuckdbWorkerPool, "is_duckdb_backend", return_value=True):
        assert DuckdbWorkerPool.should_apply_process_pool_scope(
            mode="auto",
            use_process_pool=True,
        )
    with patch.object(DuckdbWorkerPool, "is_duckdb_backend", return_value=False):
        assert not DuckdbWorkerPool.should_apply_process_pool_scope(
            mode="auto",
            use_process_pool=True,
        )


def test_should_apply_off():
    assert not DuckdbWorkerPool.should_apply_process_pool_scope(
        mode="off",
        use_process_pool=True,
    )


def test_should_apply_on_requires_process():
    assert not DuckdbWorkerPool.should_apply_process_pool_scope(
        mode="on",
        use_process_pool=False,
    )


def test_scope_does_not_create_holder_after_suspend():
    """suspend 后不得 DataManager()，否则 wait_for_main_end 会死等 600s。"""
    DuckdbWorkerPool._main_suspend_depth = 0
    created_after_suspend = []

    def _resolve(*_args, **_kwargs):
        if DuckdbWorkerPool._main_suspend_depth > 0:
            created_after_suspend.append(True)
            raise AssertionError("must not create holder while DuckDB pool is suspended")
        return None

    try:
        with patch.object(DuckdbWorkerPool, "is_duckdb_backend", return_value=True), patch.object(
            DuckdbWorkerPool, "prepare_main_for_worker_pool"
        ), patch.object(DuckdbWorkerPool, "wait_pool_children_done"), patch.object(
            DuckdbWorkerPool, "ensure_data_manager_restored", return_value=None
        ), patch.object(
            DuckdbWorkerPool, "resolve_holder", side_effect=_resolve
        ):
            with DuckdbWorkerPool.duckdb_worker_pool_main_process(None) as dm:
                assert dm is None
                assert DuckdbWorkerPool._main_suspend_depth == 1
        assert created_after_suspend == []
        assert DuckdbWorkerPool._main_suspend_depth == 0
    finally:
        DuckdbWorkerPool._main_suspend_depth = 0
        DuckdbWorkerPool._suspend_thread_ident = None


def test_wait_for_main_end_fails_on_owner_thread():
    """同一线程在 suspend 期间打开主库必须立刻失败，不能死等 600s。"""
    import threading

    DuckdbWorkerPool._main_suspend_depth = 1
    DuckdbWorkerPool._suspend_thread_ident = threading.get_ident()
    try:
        import pytest

        with pytest.raises(RuntimeError, match="禁止再打开主库"):
            DuckdbWorkerPool.wait_for_main_duckdb_worker_pool_end(timeout_sec=1)
    finally:
        DuckdbWorkerPool._main_suspend_depth = 0
        DuckdbWorkerPool._suspend_thread_ident = None
