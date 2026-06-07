"""
跨 backend 的 schema 字段定义（类型语义）。

各 engine 的 ``schema_parser`` 负责将这些定义转为本方言 DDL。
"""
from .base import Field
from .string import StringField, CharField, TextField
from .numeric import (
    IntField,
    BigIntField,
    SmallIntField,
    FloatField,
    DoubleField,
    DecimalField,
)
from .boolean import BooleanField
from .datetime import DateField, DateTimeField, TimestampField, TimeField
from .json import JsonField
from .uuid import UuidField
from .blob import BlobField
from .enum import EnumField
from typing import Dict, Any

__all__ = [
    "Field",
    "StringField",
    "CharField",
    "TextField",
    "IntField",
    "BigIntField",
    "SmallIntField",
    "FloatField",
    "DoubleField",
    "DecimalField",
    "BooleanField",
    "DateField",
    "DateTimeField",
    "TimestampField",
    "TimeField",
    "JsonField",
    "UuidField",
    "BlobField",
    "EnumField",
]


def from_dict(field_dict: Dict[str, Any]) -> Field:
    """从字典创建 Field 对象（工厂方法）。"""
    field_type = field_dict.get("type", "").upper()
    name = field_dict.get("name")
    is_required = field_dict.get("isRequired", False)
    default = field_dict.get("default")
    comment = field_dict.get("comment") or field_dict.get("description")
    auto_increment = field_dict.get("autoIncrement", False) or field_dict.get(
        "isAutoIncrement", False
    )
    nullable = field_dict.get("nullable", field_dict.get("isNullable", True))

    if not name:
        raise ValueError("字段定义缺少 'name' 字段")
    if not field_type:
        raise ValueError(f"字段 '{name}' 缺少 'type' 字段")

    if field_type in ["VARCHAR", "CHAR"]:
        length = field_dict.get("length")
        if field_type == "CHAR":
            return CharField(
                name, length, is_required, default, comment, nullable=nullable
            )
        return StringField(
            name, length, is_required, default, comment, nullable=nullable
        )
    if field_type == "TEXT":
        return TextField(name, is_required, default, comment, nullable=nullable)
    if field_type in ["INT", "INTEGER"]:
        return IntField(
            name, is_required, default, comment, auto_increment, nullable=nullable
        )
    if field_type == "BIGINT":
        return BigIntField(
            name, is_required, default, comment, auto_increment, nullable=nullable
        )
    if field_type == "SMALLINT":
        return SmallIntField(name, is_required, default, comment, nullable=nullable)
    if field_type == "TINYINT":
        length = field_dict.get("length")
        if length == 1:
            return BooleanField(name, is_required, default, comment, nullable=nullable)
        return IntField(
            name, is_required, default, comment, auto_increment, nullable=nullable
        )
    if field_type in ["FLOAT", "REAL"]:
        return FloatField(name, is_required, default, comment, nullable=nullable)
    if field_type == "DOUBLE":
        return DoubleField(name, is_required, default, comment, nullable=nullable)
    if field_type in ["DECIMAL", "NUMERIC"]:
        length = field_dict.get("length")
        return DecimalField(
            name, length, is_required, default, comment, nullable=nullable
        )
    if field_type == "BOOLEAN":
        return BooleanField(name, is_required, default, comment, nullable=nullable)
    if field_type == "DATE":
        return DateField(name, is_required, default, comment, nullable=nullable)
    if field_type == "DATETIME":
        return DateTimeField(name, is_required, default, comment, nullable=nullable)
    if field_type == "TIMESTAMP":
        return TimestampField(name, is_required, default, comment, nullable=nullable)
    if field_type == "TIME":
        return TimeField(name, is_required, default, comment, nullable=nullable)
    if field_type == "JSON":
        return JsonField(
            name,
            is_jsonb=False,
            is_required=is_required,
            default=default,
            comment=comment,
            nullable=nullable,
        )
    if field_type == "JSONB":
        return JsonField(
            name,
            is_jsonb=True,
            is_required=is_required,
            default=default,
            comment=comment,
            nullable=nullable,
        )
    if field_type == "UUID":
        return UuidField(name, is_required, default, comment, nullable=nullable)
    if field_type == "BLOB":
        return BlobField(name, is_required, default, comment, nullable=nullable)
    if field_type == "ENUM":
        values = field_dict.get("values", [])
        return EnumField(
            name, values, is_required, default, comment, nullable=nullable
        )
    raise ValueError(f"不支持的字段类型: {field_type} (字段: {name})")


Field.from_dict = staticmethod(from_dict)
