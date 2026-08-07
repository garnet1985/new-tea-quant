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
