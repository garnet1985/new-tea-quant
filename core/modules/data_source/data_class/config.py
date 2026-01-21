from typing import Any, Dict
from loguru import logger
from core.global_enums.enums import UpdateMode


class DataSourceConfig:
    """
    DataSource Config class
    
    支持从 dict 创建，并提供配置验证功能。
    """
    
    def __init__(self, config_dict: Dict[str, Any], data_source_name: str = None):
        """
        从字典创建 DataSourceConfig
        
        Args:
            config_dict: 配置字典
            data_source_name: 数据源名称（用于错误提示）
        """
        self._config_dict = config_dict or {}
        self._data_source_name = data_source_name or "unknown"
        
        # 验证配置
        self.validate()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（兼容 dict 接口）"""
        return self._config_dict.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """支持 dict 风格的访问"""
        return self._config_dict[key]
    
    def __contains__(self, key: str) -> bool:
        """支持 'key in config' 语法"""
        return key in self._config_dict
    
    def validate(self) -> None:
        """
        验证 config 配置是否完整（根据 renew_mode 验证必填字段）。
        
        规则：
        - incremental 模式：必须配置 table_name 和 date_field
        - rolling 模式：必须配置 table_name、date_field、rolling_unit、rolling_length
        
        Raises:
            ValueError: 如果配置不完整
        """
        if not self._config_dict:
            return  # 空 config 不验证
        
        renew_mode = (self._config_dict.get("renew_mode") or "").lower()
        
        # Incremental 模式验证
        if renew_mode == UpdateMode.INCREMENTAL.value:
            table_name = self._config_dict.get("table_name")
            date_field = self._config_dict.get("date_field")
            if not table_name or not date_field:
                raise ValueError(
                    f"Data source '{self._data_source_name}' 使用 incremental renew_mode，"
                    f"必须显式配置 table_name 和 date_field，"
                    f"当前配置: table_name={table_name}, date_field={date_field}"
                )
        
        # Rolling 模式验证
        elif renew_mode == UpdateMode.ROLLING.value:
            table_name = self._config_dict.get("table_name")
            date_field = self._config_dict.get("date_field")
            rolling_unit = self._config_dict.get("rolling_unit")
            rolling_length = self._config_dict.get("rolling_length")
            
            if not table_name or not date_field:
                raise ValueError(
                    f"Data source '{self._data_source_name}' 使用 rolling renew_mode，"
                    f"必须显式配置 table_name 和 date_field，"
                    f"当前配置: table_name={table_name}, date_field={date_field}"
                )
            
            if not rolling_unit or not rolling_length:
                raise ValueError(
                    f"Data source '{self._data_source_name}' 使用 rolling renew_mode，"
                    f"必须显式配置 rolling_unit 和 rolling_length，"
                    f"当前配置: rolling_unit={rolling_unit}, rolling_length={rolling_length}"
                )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于兼容性）"""
        return self._config_dict.copy()