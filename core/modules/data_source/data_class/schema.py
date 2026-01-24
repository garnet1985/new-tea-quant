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


    def is_valid(self, data: Dict[str, Any]) -> bool:
        """
        验证单条数据是否符合 Schema 定义，如果符合则返回 True，否则返回 False。

        - 所有 required=True 的字段必须存在于 data 中
        - 如果字段存在且不为 None，则尝试按声明的 type 做一次宽松转换：
          - int: 接受 float/str，可转换则视为通过
          - float: 接受 int/str，可转换则视为通过
          - str: 始终可以通过 str(...) 转换
        
        Args:
            data: 待验证的数据字典
        
        Returns:
            bool: 数据是否符合 Schema 定义
        """
        if not self.fields:
            logger.warning(f"'{self.name}' 的 schema.json 中没有配置 fields，将跳过执行")
            return False

        for field_name, field_def in self.fields.items():
            # 必需字段缺失
            if field_def.required and field_name not in data:
                return False

            # 有值时做类型检查/转换
            if field_name in data and data[field_name] is not None:
                value = data[field_name]
                expected_type = field_def.type

                if not isinstance(value, expected_type):
                    try:
                        if expected_type is int and isinstance(value, (float, str)):
                            int(value)
                        elif expected_type is float and isinstance(value, (int, str)):
                            float(value)
                        elif expected_type is str:
                            str(value)
                        else:
                            return False
                    except (ValueError, TypeError):
                        return False

        return True