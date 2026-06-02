"""
DateTime Field Types - 日期时间字段类型

包含 DATE, DATETIME, TIMESTAMP, TIME 等日期时间类型。
"""
from .base import Field


class DateField(Field):
    """DATE 字段"""

    def _to_sql_impl(self, database_type: str) -> str:
        # DuckDB DATE/TIMESTAMP 不接受 YYYYMMDD 字符串；业务侧统一用 8 位文本
        if database_type == "duckdb":
            return "VARCHAR(8)"
        return "DATE"

    def get_type_name(self) -> str:
        return "date"


class DateTimeField(Field):
    """DATETIME 字段（各库映射见实现）"""

    def _to_sql_impl(self, database_type: str) -> str:
        if database_type == "duckdb":
            return "VARCHAR(19)"
        if database_type == "postgresql":
            return "TIMESTAMP"
        if database_type == 'mysql':
            return "DATETIME"
        return "TIMESTAMP"

    def get_type_name(self) -> str:
        return "datetime"


class TimestampField(Field):
    """TIMESTAMP 字段"""

    def _to_sql_impl(self, database_type: str) -> str:
        if database_type == "duckdb":
            return "VARCHAR(19)"
        return "TIMESTAMP"

    def get_type_name(self) -> str:
        return "timestamp"


class TimeField(Field):
    """TIME 字段"""

    def _to_sql_impl(self, database_type: str) -> str:
        return "TIME"

    def get_type_name(self) -> str:
        return "time"
