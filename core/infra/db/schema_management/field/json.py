"""
JSON Field Type - JSON 字段类型
"""
from typing import Any, Dict
from .base import Field


class JsonField(Field):
    """JSON 字段"""
    
    def __init__(
        self,
        name: str,
        is_jsonb: bool = False,
        is_required: bool = False,
        default: Any = None,
        comment: str = None
    ):
        self.is_jsonb = is_jsonb
        # JSON 支持 PostgreSQL 和 MySQL
        # JSONB 仅支持 PostgreSQL
        if is_jsonb:
            self.supported_databases = ['postgresql']
        else:
            self.supported_databases = ['postgresql', 'mysql']
        super().__init__(name, is_required, default, comment)
    
    def _to_sql_impl(self, database_type: str) -> str:
        if database_type == 'postgresql':
            if self.is_jsonb:
                return "JSONB"
            else:
                return "JSON"
        elif database_type == 'mysql':
            return "JSON"
        else:
            return "JSON"
    
    def get_type_name(self) -> str:
        return "jsonb" if self.is_jsonb else "json"
    
    def to_dict(self) -> Dict[str, Any]:
        result = super().to_dict()
        if self.is_jsonb:
            result['type'] = 'jsonb'
        return result
