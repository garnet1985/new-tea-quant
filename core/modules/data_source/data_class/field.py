from dataclasses import dataclass
from typing import Any, Type


@dataclass
class DataSourceField:
    """
    字段定义（轻量 data class）。

    用于描述数据源 Schema 中单个字段的类型、是否必需、默认值等信息。
    保留此类仅供 userspace 中仍使用 DataSourceSchema 的 handler schema.py 向后兼容；
    框架运行时已不再使用，schema 来自绑定表的 load_schema()。
    """

    type: Type
    required: bool = True
    description: str = ""
    default: Any = None
