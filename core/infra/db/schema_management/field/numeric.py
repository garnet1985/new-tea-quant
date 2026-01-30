"""
Numeric Field Types - 数值字段类型

包含 INT, BIGINT, SMALLINT, FLOAT, DOUBLE, DECIMAL 等数值类型。
"""
from typing import Optional, Dict, Any
from .base import Field


class IntField(Field):
    """INTEGER 字段（通用类型，所有数据库支持）"""
    
    def _supports_auto_increment(self) -> bool:
        return True
    
    def _to_sql_impl(self, database_type: str) -> str:
        if self.auto_increment:
            if database_type == 'postgresql':
                return "SERIAL"
            elif database_type == 'mysql':
                return "INT AUTO_INCREMENT"
            elif database_type == 'sqlite':
                return "INTEGER PRIMARY KEY AUTOINCREMENT"
            else:
                return "SERIAL"
        return "INTEGER"
    
    def get_type_name(self) -> str:
        return "int"


class BigIntField(Field):
    """BIGINT 字段（通用类型，所有数据库支持）"""
    
    def _supports_auto_increment(self) -> bool:
        return True
    
    def _to_sql_impl(self, database_type: str) -> str:
        if self.auto_increment:
            if database_type == 'postgresql':
                return "BIGSERIAL"
            elif database_type == 'mysql':
                return "BIGINT AUTO_INCREMENT"
            elif database_type == 'sqlite':
                return "INTEGER PRIMARY KEY AUTOINCREMENT"
            else:
                return "BIGSERIAL"
        return "BIGINT"
    
    def get_type_name(self) -> str:
        return "bigint"


class SmallIntField(Field):
    """SMALLINT 字段（通用类型，所有数据库支持）"""
    
    def _to_sql_impl(self, database_type: str) -> str:
        return "SMALLINT"
    
    def get_type_name(self) -> str:
        return "smallint"


class FloatField(Field):
    """FLOAT 字段（通用类型，所有数据库支持）"""
    
    def _to_sql_impl(self, database_type: str) -> str:
        return "FLOAT"
    
    def get_type_name(self) -> str:
        return "float"


class DoubleField(Field):
    """DOUBLE 字段（通用类型，所有数据库支持）"""
    
    def _to_sql_impl(self, database_type: str) -> str:
        if database_type == 'postgresql':
            return "DOUBLE PRECISION"
        elif database_type == 'mysql':
            return "DOUBLE"
        elif database_type == 'sqlite':
            return "REAL"
        else:
            return "DOUBLE"
    
    def get_type_name(self) -> str:
        return "double"


class DecimalField(Field):
    """DECIMAL 字段（通用类型，所有数据库支持）"""
    
    def __init__(
        self,
        name: str,
        length: Optional[str] = None,
        is_required: bool = False,
        default: Any = None,
        comment: str = None,
        nullable: bool = True,
    ):
        self.length = length  # 可以是 "10,2" 或 "10"
        super().__init__(name, is_required, default, comment, nullable=nullable)
    
    def _to_sql_impl(self, database_type: str) -> str:
        if self.length:
            return f"DECIMAL({self.length})"
        return "DECIMAL"
    
    def get_type_name(self) -> str:
        return "decimal"
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.length:
            result['length'] = self.length
        return result
