"""
MySQL 方言 — 占位符、information_schema 等 SQL 文本（无 I/O）。

连接与执行见 ``mysql.connector.MysqlConnector``。
"""
from __future__ import annotations

from typing import Any, Dict, Tuple


class MysqlSqlAdapter:
    """MySQL 方言辅助（无状态）。"""

    PLACEHOLDER = "%s"

    @staticmethod
    def normalize_query(query: str) -> str:
        """`?` → `%s`，便于上层统一写占位符。"""
        return query.replace("?", "%s")

    @staticmethod
    def table_exists_query_and_params(table_name: str) -> Tuple[str, Tuple[Any, ...]]:
        sql = """
            SELECT COUNT(*) AS count
            FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = %s
        """
        return sql, (table_name,)

    @staticmethod
    def parse_exists_count(row: Dict[str, Any]) -> bool:
        if not row:
            return False
        n = row.get("count", row.get("cnt", 0))
        return int(n) > 0 if n is not None else False
