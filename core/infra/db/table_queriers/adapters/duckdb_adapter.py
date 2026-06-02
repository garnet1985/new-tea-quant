"""
兼容层：请使用 ``core.infra.db.engines.duckdb.connector.DuckdbDomainConnection``。
"""
from core.infra.db.engines.duckdb.connector import DuckdbDomainConnection

DuckDBAdapter = DuckdbDomainConnection

__all__ = ["DuckDBAdapter", "DuckdbDomainConnection"]
