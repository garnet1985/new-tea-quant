"""
DDL 执行 — 将含多条语句的脚本按 ``;`` 拆分后逐条执行（如 DuckDB SEQUENCE + CREATE TABLE）。
"""
from __future__ import annotations

from typing import Any, List


def split_ddl_statements(sql: str) -> List[str]:
    """按分号拆分 DDL；忽略空段。"""
    if not sql or not str(sql).strip():
        return []
    parts: List[str] = []
    for chunk in str(sql).split(";"):
        stmt = chunk.strip()
        if stmt:
            parts.append(stmt)
    return parts


def execute_ddl(conn: Any, sql: str) -> None:
    """在 SchemaManager 提供的连接上执行 DDL（支持多语句）。"""
    for stmt in split_ddl_statements(sql):
        conn.execute(stmt)
