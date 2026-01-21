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

    提供最小的 validate 能力，供 handler/测试使用。
    更高层的 DataValidator 仍然可以在此之上做额外校验。
    """

    name: str
    description: str = ""
    fields: Dict[str, DataSourceField] = field(default_factory=dict)

    def validate_data(self, data: Dict[str, Any]) -> bool:
        """
        验证单条数据是否符合 Schema 定义。

        规则（与旧版 DataSourceSchema.validate 等价的最小子集）：
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

    def validate(self) -> None:
        """
        验证 Schema 本身的完整性（在发现后调用）。
        
        严重问题会抛出 ValueError 并停止执行：
        - name 不能为空
        - fields 不能为空（至少需要一个字段定义）
        
        Raises:
            ValueError: 如果 Schema 定义不完整
        """
        # 严重问题：name 为空
        if not self.name or not self.name.strip():
            raise ValueError(
                f"DataSourceSchema.name 不能为空（当前值: {repr(self.name)}）"
            )
        
        # 严重问题：fields 为空
        if not self.fields:
            raise ValueError(
                f"DataSourceSchema '{self.name}' 的 fields 不能为空，至少需要定义一个字段"
            )
        
        # 警告：description 为空（非严重问题，只记录警告）
        if not self.description or not self.description.strip():
            logger.warning(
                f"DataSourceSchema '{self.name}' 的 description 为空，建议添加描述信息"
            )