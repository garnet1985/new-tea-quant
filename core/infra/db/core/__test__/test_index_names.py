"""同名索引落到各自的表上，列检查不会把空结果当成缺列。"""
from __future__ import annotations

from contextlib import contextmanager

import duckdb
import pytest

from core.infra.db.core.schema_manager import SchemaManager, parse_duckdb_index_expressions

pytestmark = pytest.mark.force_run


def test_index_sql_is_unique_per_table():
    manager = SchemaManager(database_type="duckdb")
    sql = manager.generate_create_index_sql(
        "sys_money_supply",
        {"name": "idx_date", "fields": ["date"], "unique": True},
    )
    assert '"sys_money_supply__idx_date"' in sql
    assert 'ON "sys_money_supply"' in sql


def test_parse_duckdb_index_expressions():
    assert parse_duckdb_index_expressions("[id, term, date]") == ("id", "term", "date")
    assert parse_duckdb_index_expressions("['\"value\"']") == ("value",)


def test_same_index_name_is_created_on_each_table(tmp_path):
    db_path = tmp_path / "idx.duckdb"
    con = duckdb.connect(str(db_path))

    class Wrapper:
        def execute(self, query, params=None):
            if params is None:
                con.execute(query)
            else:
                con.execute(query, params)
            description = list(con.description or [])
            columns = [str(col[0]) for col in description if col]
            try:
                rows = list(con.fetchall() or [])
            except Exception:
                rows = []

            class Result:
                def fetchall(self_inner):
                    return rows

                @property
                def columns(self_inner):
                    return columns

                @property
                def description(self_inner):
                    return [(name, None, None, None, None, None, None) for name in columns]

            return Result()

    @contextmanager
    def factory():
        yield Wrapper()

    manager = SchemaManager(database_type="duckdb")
    for table in ("sys_cpi", "sys_money_supply"):
        manager.create_table(
            {
                "name": table,
                "primaryKey": "date",
                "fields": [
                    {"name": "date", "type": "varchar", "length": 6, "nullable": False},
                    {"name": "value", "type": "float", "nullable": True},
                ],
                "indexes": [{"name": "idx_date", "fields": ["date"], "unique": True}],
            },
            factory,
        )

    rows = con.execute(
        "SELECT table_name, index_name FROM duckdb_indexes() "
        "WHERE table_name IN ('sys_cpi', 'sys_money_supply') ORDER BY 1"
    ).fetchall()
    con.close()
    assert rows == [
        ("sys_cpi", "sys_cpi__idx_date"),
        ("sys_money_supply", "sys_money_supply__idx_date"),
    ]


def test_existing_column_coverage_is_not_duplicated(tmp_path):
    db_path = tmp_path / "covered.duckdb"
    con = duckdb.connect(str(db_path))
    con.execute('CREATE TABLE sys_areas (id INTEGER PRIMARY KEY, value VARCHAR, is_alive INTEGER)')
    con.execute('CREATE UNIQUE INDEX idx_value ON sys_areas("value")')

    class Wrapper:
        def execute(self, query, params=None):
            if params is None:
                con.execute(query)
            else:
                con.execute(query, params)
            description = list(con.description or [])
            columns = [str(col[0]) for col in description if col]
            try:
                rows = list(con.fetchall() or [])
            except Exception:
                rows = []

            class Result:
                def fetchall(self_inner):
                    return rows

            return Result()

    @contextmanager
    def factory():
        yield Wrapper()

    SchemaManager(database_type="duckdb").create_table(
        {
            "name": "sys_areas",
            "primaryKey": "id",
            "fields": [
                {"name": "id", "type": "int", "nullable": False},
                {"name": "value", "type": "varchar", "length": 64, "nullable": True},
                {"name": "is_alive", "type": "tinyint", "nullable": True},
            ],
            "indexes": [
                {"name": "idx_value", "fields": ["value"], "unique": True},
                {"name": "idx_is_alive", "fields": ["is_alive"]},
            ],
        },
        factory,
    )
    rows = con.execute(
        "SELECT index_name FROM duckdb_indexes() WHERE table_name = 'sys_areas' ORDER BY 1"
    ).fetchall()
    con.close()
    assert ("idx_value",) in rows
    assert ("sys_areas__idx_value",) not in rows
    assert ("sys_areas__idx_is_alive",) in rows
