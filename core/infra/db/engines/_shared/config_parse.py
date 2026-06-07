"""database.json 合并后的配置校验与默认值（挂载 Engine 之前）。"""
from __future__ import annotations

from typing import Dict


def parse_database_config(config: Dict) -> Dict:
    """
    解析并验证数据库配置；补足 ``batch_write`` 等默认值。

    Raises:
        ValueError: 配置不完整或无效
    """
    database_type = config.get("database_type")
    if not database_type:
        raise ValueError("配置中缺少 'database_type' 字段")

    database_type = database_type.lower()
    valid_types = ["postgresql", "mysql", "duckdb"]
    if database_type not in valid_types:
        raise ValueError(
            f"不支持的数据库类型: {database_type}，"
            f"支持的类型: {', '.join(valid_types)}"
        )

    db_config = config.get(database_type)
    if not db_config:
        raise ValueError(
            f"配置中缺少 '{database_type}' 数据库配置，"
            f"请确保配置中包含 '{database_type}' 字段"
        )

    if database_type == "duckdb":
        domains = db_config.get("domains")
        if not isinstance(domains, dict) or not domains:
            raise ValueError(
                "DuckDB 配置中缺少非空 'domains' 对象（data / tag / strategy）"
            )
        from core.infra.db.storage_registry import STORAGE_DOMAINS

        for domain in STORAGE_DOMAINS:
            if domain not in domains:
                raise ValueError(f"DuckDB domains 缺少域: {domain}")
            if not domains[domain].get("db_path"):
                raise ValueError(f"DuckDB 域 {domain!r} 缺少 db_path")
    else:
        required_fields = ["host", "port", "database", "user", "password"]
        missing_fields = [f for f in required_fields if f not in db_config]
        if missing_fields:
            raise ValueError(
                f"{database_type.upper()} 配置中缺少必需字段: {', '.join(missing_fields)}"
            )

    if database_type == "postgresql":
        db_config["pgsql_schema"] = db_config.get("default_pgsql_schema")

    if "batch_write" not in config:
        config["batch_write"] = {
            "enable": True,
            "batch_size": 1000,
            "flush_interval": 5.0,
        }
    else:
        batch_write = config["batch_write"]
        if "enable" not in batch_write:
            batch_write["enable"] = True
        if "batch_size" not in batch_write:
            batch_write["batch_size"] = 1000
        if "flush_interval" not in batch_write:
            batch_write["flush_interval"] = 5.0

    config["database_type"] = database_type
    return config
