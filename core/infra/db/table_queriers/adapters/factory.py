"""
DatabaseAdapterFactory - 数据库适配器工厂

PostgreSQL / MySQL：单连接适配器。
DuckDB：仅通过 create_duckdb_domain_adapter 按存储域创建（由 ConnectionManager 调用）。
"""
from typing import Dict, Any
import logging

from .base_adapter import BaseDatabaseAdapter

logger = logging.getLogger(__name__)


class DatabaseAdapterFactory:
    """根据配置创建 PostgreSQL / MySQL 适配器。"""

    @staticmethod
    def create_duckdb_domain_adapter(
        domain_config: Dict[str, Any],
        *,
        is_verbose: bool = False,
    ) -> BaseDatabaseAdapter:
        """为单个 DuckDB 存储域创建并连接适配器。"""
        from .duckdb_adapter import DuckDBAdapter
        from core.infra.db.helpers.duckdb_paths import resolve_duckdb_db_path

        cfg = dict(domain_config or {})
        if cfg.get("db_path"):
            cfg["db_path"] = resolve_duckdb_db_path(str(cfg["db_path"]))
        adapter = DuckDBAdapter(cfg, is_verbose=is_verbose)
        adapter.connect()
        return adapter

    @staticmethod
    def create(config: Dict[str, Any], is_verbose: bool = False) -> BaseDatabaseAdapter:
        """创建 PostgreSQL 或 MySQL 适配器。"""
        database_type = config.get("database_type", "postgresql").lower()

        if database_type == "duckdb":
            raise ValueError(
                "DuckDB 请由 ConnectionManager 按 domains 创建适配器，"
                "不要调用 DatabaseAdapterFactory.create()"
            )

        if database_type == "postgresql":
            from .postgresql_adapter import PostgreSQLAdapter

            pg_config = config.get("postgresql")
            if not pg_config:
                raise ValueError("PostgreSQL 配置缺失，请提供 'postgresql' 配置项")

            adapter = PostgreSQLAdapter(pg_config, is_verbose=is_verbose)
            adapter.connect()
            return adapter

        if database_type == "mysql":
            from .mysql_adapter import MySQLAdapter

            mysql_config = config.get("mysql")
            if not mysql_config:
                raise ValueError("MySQL 配置缺失，请提供 'mysql' 配置项")

            adapter = MySQLAdapter(mysql_config, is_verbose=is_verbose)
            adapter.connect()
            return adapter

        raise ValueError(
            f"不支持的数据库类型: {database_type}，"
            f"支持的类型: 'postgresql', 'mysql'"
        )
