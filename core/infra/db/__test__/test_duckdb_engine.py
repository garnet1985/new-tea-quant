"""DuckdbEngine / WritePipeline 单元测试（Mock 连接）。"""
from unittest.mock import MagicMock, patch

import pytest

from core.infra.db.engines import build_engine_meta, create_engine
from core.infra.db.engines.duckdb.engine import DuckdbEngine
from core.infra.db.engines.duckdb.table_operator import DuckdbTableOperator


DUCKDB_CONFIG = {
    "database_type": "duckdb",
    "duckdb": {
        "domains": {
            "data": {"db_path": "data.duckdb"},
            "tag": {"db_path": "tag.duckdb"},
            "strategy": {"db_path": "strategy.duckdb"},
        },
    },
}


@pytest.fixture
def duckdb_engine():
    meta = build_engine_meta(DUCKDB_CONFIG, is_verbose=False)
    engine = create_engine(meta)
    assert isinstance(engine, DuckdbEngine)
    engine.rebuild_table_file_map(table_to_domain={"sys_stock_list": "data"})
    with patch.object(engine.connector, "connect_all_domains"), patch.object(
        engine.connector, "close_all"
    ):
        engine._write_pipelines = {}
        engine._initialized = True
        for domain in ("data", "tag", "strategy"):
            mock_pipeline = MagicMock()
            mock_pipeline.submit.return_value = 2
            engine._write_pipelines[domain] = mock_pipeline
    yield engine
    with patch.object(engine.connector, "close_all"):
        engine.close()


def test_duckdb_engine_resolve_domain(duckdb_engine):
    assert duckdb_engine.resolve_domain("sys_stock_list") == "data"
    with pytest.raises(KeyError):
        duckdb_engine.resolve_domain("unknown_table")


def test_duckdb_engine_file_map_for_table(duckdb_engine):
    fm = duckdb_engine.file_map_for_table("sys_stock_list")
    assert fm.domain == "data"
    assert fm.db_path == "data.duckdb"


def test_duckdb_table_operator_cached(duckdb_engine):
    a = duckdb_engine.table_operator("sys_stock_list")
    b = duckdb_engine.table_operator("sys_stock_list")
    assert a is b
    assert isinstance(a, DuckdbTableOperator)


def test_duckdb_insert_routes_to_pipeline(duckdb_engine):
    op = duckdb_engine.table_operator("sys_stock_list")
    n = op.insert([{"id": "1"}], None)
    assert n == 2
    duckdb_engine._write_pipelines["data"].submit.assert_called()
