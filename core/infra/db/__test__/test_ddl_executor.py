"""DDL 多语句拆分与执行。"""
from unittest.mock import Mock

from core.infra.db.engines._shared.ddl_executor import execute_ddl, split_ddl_statements


def test_split_ddl_statements_sequence_and_table():
    sql = (
        "CREATE SEQUENCE IF NOT EXISTS seq_t_id START 1;\n"
        "CREATE TABLE IF NOT EXISTS t (id INT);\n"
    )
    parts = split_ddl_statements(sql)
    assert len(parts) == 2
    assert parts[0].startswith("CREATE SEQUENCE")
    assert parts[1].startswith("CREATE TABLE")


def test_execute_ddl_runs_each_statement():
    conn = Mock()
    execute_ddl(conn, "CREATE SEQUENCE seq START 1; CREATE TABLE t (id INT);")
    assert conn.execute.call_count == 2
