"""
ENUM Field Type - ENUM 字段类型
"""
from typing import List, Dict, Any
from .base import Field


class EnumField(Field):
    """ENUM 字段（通用类型，所有数据库支持，MySQL 使用原生 ENUM，其他使用 CHECK）"""
    
    def __init__(
        self,
        name: str,
        values: List[str],
        is_required: bool = False,
        default: Any = None,
        comment: str = None,
        nullable: bool = True,
    ):
        self.values = values or []
        super().__init__(name, is_required, default, comment, nullable=nullable)
    
    def validate(self) -> None:
        super().validate()
        if not self.values:
            raise ValueError(f"ENUM 字段 '{self.name}' 必须提供 values 列表")
    
    def _to_sql_impl(self, database_type: str) -> str:
        # 转义单引号
        escaped_values = []
        for v in self.values:
            escaped_v = v.replace("'", "''")
            escaped_values.append(f"'{escaped_v}'")
        values_str = ', '.join(escaped_values)
        
        if database_type == 'postgresql':
            # PostgreSQL 使用 CHECK 约束
            return f"VARCHAR(255) CHECK ({self.name} IN ({values_str}))"
        elif database_type == 'mysql':
            return f"ENUM({values_str})"
        elif database_type == 'sqlite':
            # SQLite 使用 CHECK 约束
            return f"VARCHAR(255) CHECK ({self.name} IN ({values_str}))"
        else:
            return "VARCHAR(255)"
    
    def get_type_name(self) -> str:
        return "enum"
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        result['values'] = self.values
        return result
