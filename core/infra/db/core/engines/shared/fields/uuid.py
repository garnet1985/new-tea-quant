"""
UUID Field Type - UUID 字段类型
"""
from .base import Field


class UuidField(Field):
    """UUID 字段（仅 PostgreSQL 支持）"""
    
    supported_databases = ['postgresql', 'duckdb']
    
    def _to_sql_impl(self, database_type: str) -> str:
        return "UUID"
    
    def get_type_name(self) -> str:
        return "uuid"
