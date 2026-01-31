from dataclasses import dataclass, field
from typing import Dict, Any
from loguru import logger

from core.modules.data_source.data_class.field import DataSourceField


@dataclass
class DataSourceSchema:
    """
    DataSource Schema 定义（轻量 data class）。

    用于描述某个数据源标准化输出的数据结构：
    - name: 数据源名称（如 "kline", "corporate_finance"）
    - description: 描述信息
    - fields: 字段定义字典 {field_name: DataSourceField}

    保留此类仅供 userspace 中仍引用 DataSourceSchema 的 handler schema.py 向后兼容；
    框架运行时已不再使用，schema 来自绑定表的 load_schema()（dict）。
    """

    name: str
    description: str = ""
    fields: Dict[str, DataSourceField] = field(default_factory=dict)

    def is_valid(self) -> bool:
        """验证单条数据是否符合 Schema 定义。"""
        if not self.name:
            logger.warning(f"'{self.name}' 的 Schema 定义中没有配置 name，将跳过执行")
            return False
        if not self.fields:
            logger.warning(f"'{self.name}' 的 Schema 定义中没有配置 fields，将跳过执行")
            return False
        if not isinstance(self.fields, dict):
            logger.warning(f"'{self.name}' 的 Schema 定义中 fields 配置错误，应是字典格式")
            return False
        return True
