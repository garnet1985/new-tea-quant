"""
BLOB Field Type - BLOB 字段类型
"""
from .base import Field


class BlobField(Field):
    """BLOB 字段（通用类型，所有数据库支持，PostgreSQL 自动映射为 BYTEA）"""
    
    def _to_sql_impl(self, database_type: str) -> str:
        if database_type == 'postgresql':
            return "BYTEA"
        return "BLOB"
    
    def get_type_name(self) -> str:
        return "blob"
