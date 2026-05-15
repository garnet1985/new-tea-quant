"""
从已连接数据库读取表 / 列 / 索引清单，用于裁剪迁移 plan（避免重复 DDL）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, Set

from core.infra.db.helpers.db_helpers import DBHelper

if TYPE_CHECKING:
    from core.infra.db.db_manager import DatabaseManager


@dataclass
class DatabaseCatalog:
    """当前库中与 ``core/tables`` 逻辑表名对齐的结构快照（仅名称级）。"""

    tables: Set[str] = field(default_factory=set)
    columns: Dict[str, Set[str]] = field(default_factory=dict)
    indexes: Dict[str, Set[str]] = field(default_factory=dict)

    def has_table(self, table_name: str) -> bool:
        return table_name in self.tables

    def has_column(self, table_name: str, column_name: str) -> bool:
        return column_name in self.columns.get(table_name, set())

    def has_index(self, table_name: str, index_name: str) -> bool:
        return index_name in self.indexes.get(table_name, set())


def _pgsql_schema(config: dict) -> str:
    pg = config.get("postgresql") or {}
    return pg.get("pgsql_schema") or pg.get("default_pgsql_schema") or "public"


def introspect_database(db: "DatabaseManager") -> DatabaseCatalog:
    """
    查询 ``information_schema``（及 PostgreSQL ``pg_indexes``）构建 :class:`DatabaseCatalog`。

    须在 ``DatabaseManager.initialize()`` 之后调用。
    """
    if not db.adapter:
        raise RuntimeError("DatabaseManager 未初始化，无法 introspection")

    cfg = db.config
    db_type = DBHelper.normalize_database_type(cfg)
    catalog = DatabaseCatalog()

    if db_type == "postgresql":
        schema = _pgsql_schema(cfg)
        tables = db.execute_sync_query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            """,
            (schema,),
        )
        catalog.tables = {str(r["table_name"]) for r in tables}

        if catalog.tables:
            cols = db.execute_sync_query(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = %s
                """,
                (schema,),
            )
            for row in cols:
                t, c = str(row["table_name"]), str(row["column_name"])
                catalog.columns.setdefault(t, set()).add(c)

            idx_rows = db.execute_sync_query(
                """
                SELECT tablename, indexname
                FROM pg_indexes
                WHERE schemaname = %s
                """,
                (schema,),
            )
            for row in idx_rows:
                t, ix = str(row["tablename"]), str(row["indexname"])
                catalog.indexes.setdefault(t, set()).add(ix)

    elif db_type == "mysql":
        tables = db.execute_sync_query(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'
            """
        )
        catalog.tables = {str(r["table_name"]) for r in tables}

        cols = db.execute_sync_query(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
            """
        )
        for row in cols:
            t, c = str(row["table_name"]), str(row["column_name"])
            catalog.columns.setdefault(t, set()).add(c)

        idx_rows = db.execute_sync_query(
            """
            SELECT table_name, index_name
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
            """
        )
        for row in idx_rows:
            t, ix = str(row["table_name"]), str(row["index_name"])
            catalog.indexes.setdefault(t, set()).add(ix)
    else:
        raise ValueError(f"introspection 不支持的数据库类型: {db_type}")

    return catalog
