"""
DataSource Schema - 数据源 Schema 定义

用于定义数据源的数据结构规范。
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Type, Union


@dataclass
class Field:
    """
    字段定义
    
    用于定义数据源中的字段类型、是否必需等信息。
    """
    type: Type
    required: bool = True
    description: str = ""
    default: Any = None
    
    def __init__(self, type: Type, required: bool = True, description: str = "", default: Any = None):
        self.type = type
        self.required = required
        self.description = description
        self.default = default


@dataclass
class DataSourceSchema:
    """
    数据源 Schema 定义
    
    用于定义数据源的数据结构规范，包括：
    - name: 数据源名称
    - description: 描述
    - schema: 字段定义字典
    """
    name: str
    description: str = ""
    schema: Dict[str, Field] = field(default_factory=dict)
    
    def __init__(self, name: str, description: str = "", schema: Dict[str, Field] = None):
        self.name = name
        self.description = description
        self.schema = schema or {}
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """
        验证数据是否符合 Schema 定义
        
        Args:
            data: 要验证的数据字典
            
        Returns:
            是否符合规范
        """
        # 检查必需字段
        for field_name, field_def in self.schema.items():
            if field_def.required and field_name not in data:
                return False
            
            # 检查类型（如果提供了值）
            if field_name in data and data[field_name] is not None:
                value = data[field_name]
                expected_type = field_def.type
                # 允许类型转换（如 int 可以接受 float）
                if not isinstance(value, expected_type):
                    # 尝试类型转换
                    try:
                        if expected_type == int and isinstance(value, (float, str)):
                            int(value)
                        elif expected_type == float and isinstance(value, (int, str)):
                            float(value)
                        elif expected_type == str:
                            str(value)
                        else:
                            return False
                    except (ValueError, TypeError):
                        return False
        
        return True
