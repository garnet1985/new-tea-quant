"""PgsqlEngine / PgsqlTableOperator 单元测试（Mock connector）。"""
from unittest.mock import MagicMock, patch

import pytest

from core.infra.db.core.engines import EngineConfigMeta, EngineFactory
from core.infra.db.core.engines.pgsql.engine import PgsqlEngine


PGSQL_CONFIG = {
    "database_type": "postgresql",
    "postgresql": {
        "host": "127.0.0.1",
        "port": 5432,
        "database": "test",
        "user": "u",
        "password": "p",
        "pgsql_schema": "public",
    },
}


@pytest.fixture
def pgsql_engine():
    meta = EngineConfigMeta.from_raw_config(PGSQL_CONFIG, is_verbose=False)
    engine = EngineFactory.create(meta)
    assert isinstance(engine, PgsqlEngine)
    with patch.object(engine.connector, "connect"):
        engine.initialize()
    yield engine
    engine.close()


def test_pgsql_engine_table_operator_cached(pgsql_engine):
    a = pgsql_engine.table_operator("sys_stock_list")
    b = pgsql_engine.table_operator("sys_stock_list")
    assert a is b
    assert a.table_name == "sys_stock_list"


def test_pgsql_table_operator_load(pgsql_engine):
    pgsql_engine.connector.execute_query = MagicMock(
        return_value=[{"id": "1", "name": "a"}]
    )
    op = pgsql_engine.table_operator("sys_stock_list")
    rows = op.load("id = %s", ("1",), limit=10)
    assert rows == [{"id": "1", "name": "a"}]
    sql = pgsql_engine.connector.execute_query.call_args[0][0]
    assert "LIMIT 10" in sql


def test_pgsql_table_operator_count(pgsql_engine):
    pgsql_engine.connector.execute_query = MagicMock(return_value=[{"cnt": 42}])
    op = pgsql_engine.table_operator("t")
    assert op.count() == 42


def test_pgsql_table_operator_replace_delegates_to_upsert(pgsql_engine):
    op = pgsql_engine.table_operator("t")
    with patch.object(op, "upsert", return_value=3) as upsert:
        assert op.replace([{"id": 1}], ["id"]) == 3
        upsert.assert_called_once()


def test_pgsql_engine_flush_writes_noop_without_queue(pgsql_engine):
    pgsql_engine._write_queue = None
    pgsql_engine.flush_writes()
    pgsql_engine.wait_for_writes()
