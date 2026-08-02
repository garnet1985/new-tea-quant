"""
PostgreSQL 方言 — 占位符、schema、information_schema 等 SQL 文本（无 I/O）。

连接与执行见 ``pgsql.connector.PgsqlConnector``。
"""
from __future__ import annotations

from typing import Any, Dict, Tuple


class PgsqlSqlAdapter:
    """PostgreSQL 方言辅助（无状态）。"""

    PLACEHOLDER = "%s"

    @staticmethod
    def normalize_query(query: str) -> str:
        return query.replace("?", "%s")

    @staticmethod
    def default_schema(config: Dict[str, Any]) -> str:
        return (
            config.get("pgsql_schema")
            or config.get("default_pgsql_schema")
            or "public"
        )

    @classmethod
    def table_exists_query_and_params(
        cls, config: Dict[str, Any], table_name: str
    ) -> Tuple[str, Tuple[Any, ...]]:
        schema = cls.default_schema(config)
        sql = """
            SELECT COUNT(*) AS count
            FROM information_schema.tables
            WHERE table_schema = %s AND table_name = %s
        """
        return sql, (schema, table_name)

    @staticmethod
    def parse_exists_count(row: Dict[str, Any]) -> bool:
        if not row:
            return False
        n = row.get("count", row.get("cnt", 0))
        return int(n) > 0 if n is not None else False
