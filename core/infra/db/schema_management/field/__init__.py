"""
Database Field Types - 数据库字段类型定义

使用面向对象的方式定义数据库字段类型，支持多种数据库的自动适配。
"""
from .base import Field
from .string import StringField, CharField, TextField
from .numeric import IntField, BigIntField, SmallIntField, FloatField, DoubleField, DecimalField
from .boolean import BooleanField
from .datetime import DateField, DateTimeField, TimestampField, TimeField
from .json import JsonField
from .uuid import UuidField
from .blob import BlobField
from .enum import EnumField
from typing import Dict, Any

__all__ = [
    # Base
    'Field',
    
    # String types
    'StringField',
    'CharField',
    'TextField',
    
    # Numeric types
    'IntField',
    'BigIntField',
    'SmallIntField',
    'FloatField',
    'DoubleField',
    'DecimalField',
    
    # Boolean type
    'BooleanField',
    
    # DateTime types
    'DateField',
    'DateTimeField',
    'TimestampField',
    'TimeField',
    
    # JSON type
    'JsonField',
    
    # UUID type
    'UuidField',
    
    # BLOB type
    'BlobField',
    
    # ENUM type
    'EnumField',
]


def from_dict(field_dict: Dict[str, Any]) -> Field:
    """
    从字典创建 Field 对象（工厂方法）
    
    Args:
        field_dict: 字段定义字典
        
    Returns:
        Field 对象
        
    Raises:
        ValueError: 不支持的字段类型或字段定义无效
    """
    field_type = field_dict.get('type', '').upper()
    name = field_dict.get('name')
    is_required = field_dict.get('isRequired', False)
    default = field_dict.get('default')
    comment = field_dict.get('comment') or field_dict.get('description')
    auto_increment = field_dict.get('autoIncrement', False) or field_dict.get('isAutoIncrement', False)
    
    if not name:
        raise ValueError("字段定义缺少 'name' 字段")
    
    if not field_type:
        raise ValueError(f"字段 '{name}' 缺少 'type' 字段")
    
    # 根据类型选择对应的 Field 类
    if field_type in ['VARCHAR', 'CHAR']:
        length = field_dict.get('length')
        if field_type == 'CHAR':
            return CharField(name, length, is_required, default, comment)
        else:
            return StringField(name, length, is_required, default, comment)
    
    elif field_type == 'TEXT':
        return TextField(name, is_required, default, comment)
    
    elif field_type in ['INT', 'INTEGER']:
        return IntField(name, is_required, default, comment, auto_increment)
    
    elif field_type == 'BIGINT':
        return BigIntField(name, is_required, default, comment, auto_increment)
    
    elif field_type == 'SMALLINT':
        return SmallIntField(name, is_required, default, comment)
    
    elif field_type == 'TINYINT':
        length = field_dict.get('length')
        if length == 1:
            return BooleanField(name, is_required, default, comment)
        else:
            return IntField(name, is_required, default, comment)
    
    elif field_type in ['FLOAT', 'REAL']:
        return FloatField(name, is_required, default, comment)
    
    elif field_type == 'DOUBLE':
        return DoubleField(name, is_required, default, comment)
    
    elif field_type in ['DECIMAL', 'NUMERIC']:
        length = field_dict.get('length')
        return DecimalField(name, length, is_required, default, comment)
    
    elif field_type == 'BOOLEAN':
        return BooleanField(name, is_required, default, comment)
    
    elif field_type == 'DATE':
        return DateField(name, is_required, default, comment)
    
    elif field_type == 'DATETIME':
        return DateTimeField(name, is_required, default, comment)
    
    elif field_type == 'TIMESTAMP':
        return TimestampField(name, is_required, default, comment)
    
    elif field_type == 'TIME':
        return TimeField(name, is_required, default, comment)
    
    elif field_type == 'JSON':
        return JsonField(name, is_jsonb=False, is_required=is_required, default=default, comment=comment)
    elif field_type == 'JSONB':
        # JSONB 仅支持 PostgreSQL
        return JsonField(name, is_jsonb=True, is_required=is_required, default=default, comment=comment)
    
    elif field_type == 'UUID':
        return UuidField(name, is_required, default, comment)
    
    elif field_type == 'BLOB':
        return BlobField(name, is_required, default, comment)
    
    elif field_type == 'ENUM':
        values = field_dict.get('values', [])
        return EnumField(name, values, is_required, default, comment)
    
    else:
        raise ValueError(f"不支持的字段类型: {field_type} (字段: {name})")


# 为了向后兼容，将 from_dict 添加到 Field 类（作为静态方法）
# 注意：这里使用 lambda 来避免循环引用
Field.from_dict = staticmethod(from_dict)
