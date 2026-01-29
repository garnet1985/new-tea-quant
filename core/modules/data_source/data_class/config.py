from typing import Any, Dict, Optional
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
        self._data_source_name = data_source_name

        
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（兼容 dict 接口）"""
        return self._config_dict.get(key, default)
    
    def is_valid(self) -> bool:
        """
        验证 config 配置是否完整（根据 renew_mode 验证必填字段）。
        
        规则：
        - incremental 模式：必须配置 table_name 和 date_field
        - rolling 模式：必须配置 table_name、date_field、rolling_unit、rolling_length
        
        Raises:
            ValueError: 如果配置不完整
        """

        if not self._is_valid_basic_info():
            return False

        if not self._is_valid_renew_mode():
            return False

        if not self._is_valid_group_by():
            return False

        if not self._is_valid_apis():
            return False

        return True

    def _is_valid_basic_info(self) -> bool:

        if not self._config_dict:
            logger.warning(f"'{self._data_source_name}' 的 config.json 为空，将跳过执行")
            return False

        
        if not self._data_source_name:
            logger.warning(f"'{self._data_source_name}' 的 config.json 中必须配置 data_source_name")
            return False

    def _is_valid_renew_mode(self) -> bool:
        renew_config = self.get("renew")

        if not renew_config:
            logger.warning(f"'{self._data_source_name}' 的 config.json 中必须配置 renew")
            return False

        renew_type = renew_config.get("type")
        if not renew_type:
            logger.warning(f"'{self._data_source_name}' 的 config.json 中 renew 必须配置 type")
            return False

        # Incremental 模式验证
        if renew_type == UpdateMode.INCREMENTAL.value or renew_type == UpdateMode.ROLLING.value:

            last_update_info = renew_config.get("last_update_info")
            if not last_update_info:
                logger.warning(f"'{self._data_source_name}' 的 config.json 中 renew 必须配置 last_update_info 来找到以前renew到的时间点")
                return False

            table_name = last_update_info.get("table_name")

            if not table_name:
                logger.warning(f"'{self._data_source_name}' 的 config.json 中 renew 必须配置 table_name")
                return False

            date_field = last_update_info.get("date_field")
            if not date_field:
                logger.warning(f"'{self._data_source_name}' 的 config.json 中 renew 必须配置 date_field")
                return False

            date_format = last_update_info.get("date_format")
            if not date_format:
                logger.warning(f"'{self._data_source_name}' 的 config.json 中 renew 必须配置 date_format")
                return False

            group_field = last_update_info.get("group_field")
            if self.is_per_entity() and not group_field:
                logger.warning(f"'{self._data_source_name}' 的 config.json 中 renew 必须配置 group_field")
                return False
        
        # Rolling 模式验证
        if renew_type == UpdateMode.ROLLING.value:
            # TODO: add validation for date range related info
            pass
            # last_update_info = renew_config.get("date_range")
            # if not last_update_info:
            #     logger.warning(f"'{self._data_source_name}' 的 config.json 中 renew 必须配置 date_range 来找到以前renew到的时间点")
            #     return False

        return True

    def _is_valid_group_by(self) -> bool:
        group_by = self.get_group_by()
        
        if group_by is None:
            return True

        if not isinstance(group_by, dict):
            logger.warning(f"'{self._data_source_name}' 的 config.json 中 result_group_by 必须配置为字典")
            return False

        if not group_by.get("list"):
            logger.warning(f"'{self._data_source_name}' 的 config.json 中 result_group_by 必须配置 list")
            return False

        if not group_by.get("by_key"):
            logger.warning(f"'{self._data_source_name}' 的 config.json 中 result_group_by 必须配置 by_key")
            return False

        return True
    
    # ========== 配置访问方法 ==========
    
    def get_renew_mode(self) -> UpdateMode:
        """获取 renew_mode（小写字符串）"""
        try:
            return UpdateMode.from_string(self.get("renew").get("type"))
        except ValueError:
            logger.warning(f"'{self._data_source_name}' 的 config.json 中配置的 renew_mode 无效，将跳过执行")
            return None
    
    def get_date_format(self) -> str:
        """获取 date_format（默认 "day"）"""
        return (self.get("date_format") or "day").lower()
    
    def get_table_name(self) -> str:
        """获取 table_name"""
        return self.get("table_name")
    
    def get_date_field(self) -> str:
        """获取 date_field"""
        return self.get("date_field")
    
    def get_default_date_range(self) -> Dict[str, Any]:
        """获取 default_date_range（默认空字典）"""
        return self.get("default_date_range") or {}
    
    def get_rolling_unit(self) -> str:
        """获取 rolling_unit"""
        return self.get("rolling_unit")
    
    def get_rolling_length(self) -> int:
        """获取 rolling_length"""
        return self.get("rolling_length")
    
    def get_needs_stock_grouping(self) -> Optional[bool]:
        """
        获取是否需要按股票分组查询最新日期。
        
        Returns:
            bool: True 表示需要按股票分组（如 stock_kline），False 表示不需要（如 GDP, LPR）
            None: 如果未配置，返回 None（将自动判断）
        """
        return self.get("needs_stock_grouping")
    
    def get_renew_if_over_days(self) -> Optional[Dict[str, Any]]:
        """
        获取「超过阈值才续跑」配置。

        约定：配置写在 renew 段下：

        "renew": {
          ...
          "renew_if_over_days": {
            "value": 30,
            "counting_field": "..."  # 可选，默认使用 date_field
          }
        }

        Returns:
            Dict[str, Any]: 配置字典，未配置时返回 None
        """
        renew = self.get("renew") or {}
        threshold = renew.get("renew_if_over_days")
        if not threshold or not isinstance(threshold, dict):
            return None
        return threshold

    def has_over_time_threshold(self) -> bool:
        """是否配置了「超过阈值才续跑」（renew_if_over_time_threshold / renew_if_over_days）。"""
        return self.get_renew_if_over_days() is not None

    def get_over_time_threshold(self) -> Optional[int]:
        """获取阈值数值（天数），未配置时返回 None。"""
        cfg = self.get_renew_if_over_days()
        if not cfg:
            return None
        val = cfg.get("value")
        return int(val) if val is not None else None
    
    def get_apis(self) -> Dict[str, Any]:
        """获取 apis 配置（默认空字典）"""
        return self.get("apis") or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于兼容性）"""
        return self._config_dict.copy()

    def is_per_entity(self) -> bool:
        """获取是否是按实体分组"""
        return self.get("result_group_by") is not None

    def get_group_by(self) -> Dict[str, Any]:
        """获取结果分组字段"""
        return self.get("result_group_by")

    def get_group_by_entity_list_name(self) -> str:
        """获取实体列表名称"""
        return self.get_group_by().get("list")

    def get_group_by_key(self) -> str:
        """获取实体列表分组字段"""
        return self.get_group_by().get("by_key")

    def get_date_range_required_info(self) -> Dict[str, Any]:
        """获取日期范围计算所需信息"""
        pass