"""
按方言从 information_schema 读取已有列名（SchemaManager 列同步用）。
"""
from __future__ import annotations

from typing import Any, Set, Tuple

from core.infra.db.engines._shared.query_rows import fetch_result_to_rows


def column_names_query(dialect: str, table_name: str) -> Tuple[str, tuple]:
    """返回 (sql, params)。"""
    d = str(dialect or "postgresql").strip().lower()
    name = str(table_name)
    if d == "mysql":
        return (
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = %s",
            (name,),
        )
    if d == "duckdb":
        return (
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'main' AND table_name = ?",
            (name,),
        )
    return (
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = %s",
        (name,),
    )


def fetch_column_names(dialect: str, table_name: str, conn: Any) -> Set[str]:
    """从连接读取表上已有列名。"""
    sql, params = column_names_query(dialect, table_name)
    d = str(dialect or "postgresql").strip().lower()

    if d == "duckdb":
        rel = conn.execute(sql, params)
        rows = fetch_result_to_rows(rel)
    elif hasattr(conn, "cursor"):
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall() or []
    else:
        rows = []

    names: Set[str] = set()
    for row in rows:
        if isinstance(row, dict):
            val = row.get("column_name") or row.get("COLUMN_NAME")
            if val is None and row:
                val = next(iter(row.values()))
        else:
            val = row[0] if row else None
        if val is not None:
            names.add(str(val))
    return names
