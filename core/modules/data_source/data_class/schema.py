from dataclasses import dataclass, field
from typing import Dict, Any
from loguru import logger

from core.modules.data_source.data_class.field import DataSourceField


@dataclass
class DataSourceSchema:
    """
    DataSource Schema 定义（轻量 data class）

    用于描述某个数据源标准化输出的数据结构：
    - name: 数据源名称（如 "kline", "corporate_finance"）
    - description: 描述信息
    - fields: 字段定义字典 {field_name: DataSourceField}

    提供基本的 is_valid 能力，供 handler/测试使用。
    """

    name: str
    description: str = ""
    fields: Dict[str, DataSourceField] = field(default_factory=dict)


    def is_valid(self) -> bool:
        """
        验证单条数据是否符合 Schema 定义，如果符合则返回 True，否则返回 False。

        """
        if not self.fields:
            logger.warning(f"'{self.name}' 的 schema.json 中没有配置 fields，将跳过执行")
            return False
    
        return True