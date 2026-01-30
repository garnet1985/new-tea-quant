"""
Field Base Class - 字段基类

所有字段类型都继承自此类。
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class Field(ABC):
    """
    数据库字段基类
    
    所有字段类型都继承自此类，负责：
    - 字段定义验证
    - 根据数据库类型生成对应的 SQL
    - 默认值处理
    - 数据库支持检查（严格模式）
    """
    
    # 支持的数据库列表（子类可以覆盖）
    supported_databases = ['postgresql', 'mysql', 'sqlite']
    
    def __init__(
        self,
        name: str,
        is_required: bool = False,
        default: Any = None,
        comment: str = None,
        auto_increment: bool = False,
        nullable: bool = True,
    ):
        """
        初始化字段
        
        Args:
            name: 字段名
            is_required: 是否必填（数据源必须提供该属性，缺失则拒绝）
            default: 默认值
            comment: 字段注释
            auto_increment: 是否自增（仅整数类型支持）
            nullable: 列是否允许 NULL；False 时建表 NOT NULL，仅主键/时序列等设为 False
        """
        self.name = name
        self.is_required = is_required
        self.default = default
        self.comment = comment
        self.auto_increment = auto_increment
        self.nullable = nullable
        
        # 验证字段定义
        self.validate()
    
    def validate(self) -> None:
        """
        验证字段定义是否有效
        
        Raises:
            ValueError: 字段定义无效
        """
        if not self.name:
            raise ValueError("字段名不能为空")
        
        if self.auto_increment and not self._supports_auto_increment():
            raise ValueError(f"字段类型 {self.__class__.__name__} 不支持 AUTO_INCREMENT")
    
    def _supports_auto_increment(self) -> bool:
        """检查字段类型是否支持 AUTO_INCREMENT"""
        return False
    
    def _is_supported(self, database_type: str) -> bool:
        """
        检查数据库是否支持此字段类型
        
        Args:
            database_type: 数据库类型
            
        Returns:
            是否支持
        """
        return database_type in self.supported_databases
    
    @abstractmethod
    def _to_sql_impl(self, database_type: str) -> str:
        """
        实际生成 SQL 的实现（子类实现）
        
        Args:
            database_type: 数据库类型
            
        Returns:
            字段 SQL 定义（不包含字段名）
        """
        pass
    
    def to_sql(self, database_type: str) -> str:
        """
        生成字段 SQL 定义（严格模式）
        
        Args:
            database_type: 数据库类型（'postgresql', 'mysql', 'sqlite'）
            
        Returns:
            字段 SQL 定义（不包含字段名）
            
        Raises:
            ValueError: 数据库不支持此字段类型
        """
        if not self._is_supported(database_type):
            raise ValueError(
                f"字段类型 '{self.get_type_name()}' 在 {database_type} 中不支持。"
                f"支持的数据库: {', '.join(self.supported_databases)}。"
                f"请使用兼容的类型或切换到支持的数据库。"
            )
        return self._to_sql_impl(database_type)
    
    def get_default_sql(self, database_type: str) -> str:
        """
        生成默认值 SQL
        
        Args:
            database_type: 数据库类型
            
        Returns:
            默认值 SQL 字符串，如果没有默认值返回空字符串
        """
        if self.default is None:
            return ""
        
        default_value = self.default
        
        # 处理字符串默认值
        if isinstance(default_value, str):
            default_upper = default_value.upper()
            
            # 处理 MySQL 的 ON UPDATE CURRENT_TIMESTAMP
            if 'ON UPDATE CURRENT_TIMESTAMP' in default_upper:
                # PostgreSQL/SQLite 不支持 ON UPDATE，只保留 CURRENT_TIMESTAMP
                if 'CURRENT_TIMESTAMP' in default_upper:
                    default_value = 'CURRENT_TIMESTAMP'
                else:
                    default_value = default_value.split(' ON UPDATE')[0].strip()
                    if not default_value:
                        return ""
            
            # 处理标准的时间戳默认值
            if default_value.upper() in ['CURRENT_TIMESTAMP', 'CURRENT_DATE', 'CURRENT_TIME']:
                return f" DEFAULT {default_value}"
            
            # 字符串默认值需要加引号
            escaped = default_value.replace("'", "''")
            return f" DEFAULT '{escaped}'"
        
        # 非字符串默认值
        return f" DEFAULT {default_value}"
    
    def get_not_null_sql(self) -> str:
        """生成 NOT NULL SQL（由 nullable 决定，与 isRequired 分离）"""
        if not self.nullable and not self.auto_increment:
            return " NOT NULL"
        return ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于向后兼容）"""
        result = {
            'name': self.name,
            'type': self.get_type_name(),
            'isRequired': self.is_required,
            'nullable': self.nullable,
        }
        
        if self.default is not None:
            result['default'] = self.default
        
        if self.comment:
            result['comment'] = self.comment
        
        if self.auto_increment:
            result['autoIncrement'] = True
        
        return result
    
    @abstractmethod
    def get_type_name(self) -> str:
        """获取字段类型名称（用于序列化）"""
        pass
