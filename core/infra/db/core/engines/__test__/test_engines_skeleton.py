"""Engine mount 架构骨架测试。"""
import pytest

pytestmark = pytest.mark.force_run

from core.infra.db.core.engines import (
    DbEngineAbc,
    DbTableAbc,
    EngineConfigMeta,
    EngineFactory,
)
from core.infra.db.core.engines.duckdb.engine import DuckdbEngine
from core.infra.db.core.engines.mysql.engine import MysqlEngine
from core.infra.db.core.engines.pgsql.engine import PgsqlEngine
from core.infra.db.core.engines.shared.config_parse import parse_database_config

_MYSQL = {
    "host": "127.0.0.1",
    "port": 3306,
    "database": "d",
    "user": "u",
    "password": "p",
}
_PGSQL = {
    "host": "127.0.0.1",
    "port": 5432,
    "database": "d",
    "user": "u",
    "password": "p",
}
_DUCKDB = {
    "domains": {
        "data": {"db_path": "data.duckdb"},
        "tag": {"db_path": "tag.duckdb"},
        "strategy": {"db_path": "strategy.duckdb"},
    },
}


def _meta(engine_key: str):
    raw = {"database_type": engine_key, engine_key: _MYSQL if engine_key == "mysql" else _PGSQL if engine_key == "postgresql" else _DUCKDB}
    return EngineConfigMeta.from_raw_config(parse_database_config(raw))


@pytest.mark.parametrize(
    "engine_key,expected_cls",
    [
        ("mysql", MysqlEngine),
        ("postgresql", PgsqlEngine),
        ("duckdb", DuckdbEngine),
    ],
)
def test_create_engine_by_key(engine_key, expected_cls):
    engine = EngineFactory.create(_meta(engine_key))
    assert isinstance(engine, expected_cls)
    assert isinstance(engine, DbEngineAbc)


def test_table_operator_returns_db_table_abc():
    engine = EngineFactory.create(_meta("mysql"))
    op = engine.table_operator("sys_stock_list")
    assert isinstance(op, DbTableAbc)
    assert op.table_name == "sys_stock_list"
    assert engine.table_operator("sys_stock_list") is op


def test_db_table_abc_concrete_helpers():
    op = EngineFactory.create(_meta("mysql")).table_operator("t")
    assert op.replace is not op.upsert
    assert op.insert_many is not op.insert
