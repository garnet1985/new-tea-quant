"""
String Field Types - 字符串字段类型

包含 VARCHAR, CHAR, TEXT 等字符串类型。
"""
from typing import Optional, Dict, Any
from .base import Field


class StringField(Field):
    """VARCHAR 字段（通用类型，所有数据库支持）"""
    
    def __init__(
        self,
        name: str,
        length: Optional[int] = None,
        is_required: bool = False,
        default: Any = None,
        comment: str = None
    ):
        self.length = length
        super().__init__(name, is_required, default, comment)
    
    def validate(self) -> None:
        super().validate()
        if self.length is not None and self.length <= 0:
            raise ValueError(f"VARCHAR 字段 '{self.name}' 的长度必须大于 0")
    
    def _to_sql_impl(self, database_type: str) -> str:
        if self.length:
            return f"VARCHAR({self.length})"
        return "VARCHAR(255)"  # 默认长度
    
    def get_type_name(self) -> str:
        return "varchar"
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.length:
            result['length'] = self.length
        return result


class CharField(Field):
    """CHAR 字段（通用类型，所有数据库支持）"""
    
    def __init__(
        self,
        name: str,
        length: Optional[int] = None,
        is_required: bool = False,
        default: Any = None,
        comment: str = None
    ):
        self.length = length or 1
        super().__init__(name, is_required, default, comment)
    
    def validate(self) -> None:
        super().validate()
        if self.length <= 0:
            raise ValueError(f"CHAR 字段 '{self.name}' 的长度必须大于 0")
    
    def _to_sql_impl(self, database_type: str) -> str:
        return f"CHAR({self.length})"
    
    def get_type_name(self) -> str:
        return "char"
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result['length'] = self.length
        return result


class TextField(Field):
    """TEXT 字段（通用类型，所有数据库支持）"""
    
    def _to_sql_impl(self, database_type: str) -> str:
        return "TEXT"
    
    def get_type_name(self) -> str:
        return "text"
