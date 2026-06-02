"""
兼容层：请使用 ``core.infra.db.engines.mysql.connector.MysqlConnector``。
"""
from core.infra.db.engines.mysql.connector import MysqlConnector, MySQLAdapter

__all__ = ["MysqlConnector", "MySQLAdapter"]
