from dataclasses import dataclass
from typing import Any, Type


@dataclass
class DataSourceField:
    """
    字段定义（轻量 data class）

    用于描述数据源 Schema 中单个字段的类型、是否必需、默认值等信息。
    """

    type: Type
    required: bool = True
    description: str = ""
    default: Any = None