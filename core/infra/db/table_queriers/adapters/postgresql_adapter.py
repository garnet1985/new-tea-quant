"""
兼容层：请使用 ``core.infra.db.engines.pgsql.connector.PgsqlConnector``。
"""
from core.infra.db.engines.pgsql.connector import PgsqlConnector, PostgreSQLAdapter

__all__ = ["PgsqlConnector", "PostgreSQLAdapter"]
