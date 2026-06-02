"""
DuckDB 方言 — 占位符、information_schema 等 SQL 文本（无 I/O）。
"""
from __future__ import annotations

from typing import Any, Dict, Tuple


class DuckdbSqlAdapter:
    PLACEHOLDER = "?"

    @staticmethod
    def normalize_query(query: str) -> str:
        """`%s` → `?`（DuckDB 原生占位符）。"""
        return query.replace("%s", "?")

    @staticmethod
    def table_exists_query_and_params(table_name: str) -> Tuple[str, Tuple[Any, ...]]:
        sql = """
            SELECT COUNT(*) AS count
            FROM information_schema.tables
            WHERE table_schema = 'main' AND table_name = ?
        """
        return sql, (table_name,)

    @staticmethod
    def parse_exists_count(row: Dict[str, Any]) -> bool:
        if not row:
            return False
        val = row.get("count") or row.get("COUNT") or row.get("cnt") or 0
        return int(val) > 0 if val is not None else False
