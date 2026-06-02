"""
跨 backend 的 schema 字段定义（类型语义）。

各 engine 的 ``schema_parser`` 负责将这些定义转为本方言 DDL。
实现暂在 ``schema_management.field``，此处为迁移入口。
"""
from core.infra.db.schema_management.field import *  # noqa: F403

from core.infra.db.schema_management.field import (
    Field,
    from_dict,
)

__all__ = [
    "Field",
    "from_dict",
]
