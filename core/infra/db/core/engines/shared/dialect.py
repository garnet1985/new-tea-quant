"""跨 backend 的 SQL 方言：类型归一、标识符引用、表名限定。"""
from __future__ import annotations

from typing import Dict, List

from core.infra.db.core.engines.shared.sql_identifiers import quote_ddl_identifier


def normalize_database_type(config: Dict) -> str:
    """归一化为 postgresql | mysql | duckdb。"""
    raw = config.get("database_type") or "postgresql"
    t = str(raw).lower()
    if t in ("postgresql", "postgres", "pg"):
        return "postgresql"
    if t in ("mysql", "mariadb"):
        return "mysql"
    if t == "duckdb":
        return "duckdb"
    return "postgresql"


def sql_dialect_for_upsert(config: Dict) -> str:
    """批量 upsert 方言（DuckDB 与 PostgreSQL 同为 ON CONFLICT）。"""
    t = normalize_database_type(config)
    if t == "duckdb":
        return "postgresql"
    return t


def sql_dialect_for_schema(config: Dict) -> str:
    """DDL / 字段类型生成方言。"""
    return normalize_database_type(config)


def quote_identifier(config: Dict, name: str) -> str:
    """按 ``config['database_type']`` 引用单个标识符。"""
    return quote_ddl_identifier(normalize_database_type(config), name)


def quote_identifier_for_dialect(database_type: str, name: str) -> str:
    """在仅有方言字符串时引用标识符。"""
    return quote_ddl_identifier(database_type, name)


def quote_identifier_list(config: Dict, names: List[str]) -> str:
    """逗号分隔的已引用列名列表。"""
    return ", ".join(quote_identifier(config, n) for n in names)


def sql_qualify_table_name(config: Dict, logical_name: str) -> str:
    """
    逻辑表名 → SQL 表标识。

    - 已含 schema（含 ``.``）时原样返回
    - PostgreSQL: ``{pgsql_schema}.table``
    - MySQL / DuckDB: 裸表名
    """
    name = logical_name.strip()
    if not name:
        raise ValueError("表名为空")
    if "." in name:
        return name
    t = normalize_database_type(config)
    if t == "postgresql":
        pg = config.get("postgresql") or {}
        schema = pg.get("pgsql_schema") or pg.get("default_pgsql_schema") or "public"
        return f"{schema}.{name}"
    return name
