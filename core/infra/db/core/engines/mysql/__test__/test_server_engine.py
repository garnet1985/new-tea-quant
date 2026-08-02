"""MysqlEngine / MysqlTableOperator 单元测试（Mock connector）。"""
from unittest.mock import MagicMock, patch

import pytest

from core.infra.db.core.engines import EngineConfigMeta, EngineFactory
from core.infra.db.core.engines.mysql.engine import MysqlEngine


MYSQL_CONFIG = {
    "database_type": "mysql",
    "mysql": {
        "host": "127.0.0.1",
        "port": 3306,
        "database": "test",
        "user": "u",
        "password": "p",
    },
}


@pytest.fixture
def mysql_engine():
    meta = EngineConfigMeta.from_raw_config(MYSQL_CONFIG, is_verbose=False)
    engine = EngineFactory.create(meta)
    assert isinstance(engine, MysqlEngine)
    with patch.object(engine.connector, "connect"):
        engine.initialize()
    yield engine
    engine.close()


def test_mysql_engine_table_operator_cached(mysql_engine):
    a = mysql_engine.table_operator("sys_stock_list")
    b = mysql_engine.table_operator("sys_stock_list")
    assert a is b
    assert a.table_name == "sys_stock_list"


def test_server_table_operator_load(mysql_engine):
    mysql_engine.connector.execute_query = MagicMock(
        return_value=[{"id": "1", "name": "a"}]
    )
    op = mysql_engine.table_operator("sys_stock_list")
    rows = op.load("id = %s", ("1",), limit=10)
    assert rows == [{"id": "1", "name": "a"}]
    sql = mysql_engine.connector.execute_query.call_args[0][0]
    assert "LIMIT 10" in sql


def test_server_table_operator_count(mysql_engine):
    mysql_engine.connector.execute_query = MagicMock(
        return_value=[{"cnt": 42}]
    )
    op = mysql_engine.table_operator("t")
    assert op.count() == 42


def test_server_table_operator_replace_delegates_to_upsert(mysql_engine):
    op = mysql_engine.table_operator("t")
    with patch.object(op, "upsert", return_value=3) as upsert:
        assert op.replace([{"id": 1}], ["id"]) == 3
        upsert.assert_called_once()


def test_mysql_engine_flush_writes_noop_without_queue(mysql_engine):
    mysql_engine._write_queue = None
    mysql_engine.flush_writes()
    mysql_engine.wait_for_writes()
