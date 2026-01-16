"""
DateTime Field Types - 日期时间字段类型

包含 DATE, DATETIME, TIMESTAMP, TIME 等日期时间类型。
"""
from .base import Field


class DateField(Field):
    """DATE 字段（通用类型，所有数据库支持，SQLite 自动映射为 TEXT）"""
    
    def _to_sql_impl(self, database_type: str) -> str:
        if database_type == 'sqlite':
            return "TEXT"
        return "DATE"
    
    def get_type_name(self) -> str:
        return "date"


class DateTimeField(Field):
    """DATETIME 字段（通用类型，所有数据库支持，自动映射）"""
    
    def _to_sql_impl(self, database_type: str) -> str:
        if database_type == 'postgresql':
            return "TIMESTAMP"
        elif database_type == 'mysql':
            return "DATETIME"
        elif database_type == 'sqlite':
            return "TEXT"
        else:
            return "TIMESTAMP"
    
    def get_type_name(self) -> str:
        return "datetime"


class TimestampField(Field):
    """TIMESTAMP 字段（通用类型，所有数据库支持，SQLite 自动映射为 TEXT）"""
    
    def _to_sql_impl(self, database_type: str) -> str:
        if database_type == 'sqlite':
            return "TEXT"
        return "TIMESTAMP"
    
    def get_type_name(self) -> str:
        return "timestamp"


class TimeField(Field):
    """TIME 字段（通用类型，所有数据库支持，SQLite 自动映射为 TEXT）"""
    
    def _to_sql_impl(self, database_type: str) -> str:
        if database_type == 'sqlite':
            return "TEXT"
        return "TIME"
    
    def get_type_name(self) -> str:
        return "time"
