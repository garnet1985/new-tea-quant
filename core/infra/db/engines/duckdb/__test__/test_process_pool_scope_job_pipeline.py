"""JobPipeline 与 process_pool_scope 集成判断。"""
from unittest.mock import patch

from core.infra.db.engines.duckdb.process_pool_scope import should_apply_process_pool_scope


def test_should_apply_auto_duckdb_process():
    with patch(
        "core.infra.db.engines.duckdb.process_pool_scope.is_duckdb_backend",
        return_value=True,
    ):
        assert should_apply_process_pool_scope(
            mode="auto",
            use_process_pool=True,
        )
    with patch(
        "core.infra.db.engines.duckdb.process_pool_scope.is_duckdb_backend",
        return_value=False,
    ):
        assert not should_apply_process_pool_scope(
            mode="auto",
            use_process_pool=True,
        )


def test_should_apply_off():
    assert not should_apply_process_pool_scope(
        mode="off",
        use_process_pool=True,
    )


def test_should_apply_on_requires_process():
    assert not should_apply_process_pool_scope(
        mode="on",
        use_process_pool=False,
    )
