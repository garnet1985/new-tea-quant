"""schema_introspection — DuckDB 列名读取（无 pandas）。"""
from __future__ import annotations

import duckdb

from core.infra.db.core.engines.shared.schema_introspection import fetch_column_names


def test_fetch_column_names_duckdb(tmp_path):
    db_path = tmp_path / "meta.duckdb"
    conn = duckdb.connect(str(db_path))
    conn.execute(
        "CREATE TABLE demo (id INTEGER, factor DECIMAL(12,4), name VARCHAR)"
    )
    names = fetch_column_names("duckdb", "demo", conn)
    conn.close()
    assert names == {"id", "factor", "name"}
