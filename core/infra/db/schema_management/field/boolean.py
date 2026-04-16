"""
Boolean Field Type - 布尔字段类型
"""
from .base import Field


class BooleanField(Field):
    """BOOLEAN 字段（通用类型，所有数据库支持，自动映射）"""
    
    def _to_sql_impl(self, database_type: str) -> str:
        if database_type == 'postgresql':
            return "BOOLEAN"
        if database_type == 'mysql':
            return "TINYINT(1)"
        return "BOOLEAN"
    
    def get_type_name(self) -> str:
        return "boolean"
