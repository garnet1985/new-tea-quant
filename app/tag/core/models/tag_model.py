from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class TagModel:
    """
    Tag Model (Tag Definition Model)
    
    使用流程：
    1. 创建实例：tag = TagModel()
    2. 从 settings 配置：tag.create_from_settings(settings["tags"][i], scenario_version)
    3. 验证配置：tag.is_valid()  # 验证配置字段（tag_name, scenario_version）
    4. ensure_metadata 后：tag.is_complete()  # 验证完整性（所有字段都有值）
    
    注意：
    - 在 ensure_metadata 之前，Model 可以是不完整的（ID=None, scenario_id=None, created_at=None 等）
    - 在 ensure_metadata 之后，Model 必须是完整的（所有字段都有值）
    """

    def __init__(self, tag_setting: Dict[str, Any], scenario_version: str):
        """初始化 TagModel（所有字段为 None/False）"""
        self.id = None
        self.tag_name = None
        self.scenario_id = None
        self.scenario_version = scenario_version
        self.display_name = None
        self.description = None
        self.is_legacy = False
        self.created_at = None
        self.updated_at = None
        
        # 状态标记
        self._is_configured = False  # 是否已从 settings 配置
        self._is_ensured = False  # 是否已 ensure_metadata（完整）

        self._set_values_from_settings(tag_setting)
        self._settings = self._fill_in_default_values_to_settings(tag_setting)

    # ================================================================
    # Public APIs
    # ================================================================
    @classmethod
    def create_from_settings(cls, tag_setting: Dict[str, Any], scenario_version: str = None) -> 'TagModel':
        """
        从 settings 字典配置当前实例
        
        用于在 ensure_metadata 之前从 settings 创建配置 Model。
        配置后应立即调用 is_valid() 验证配置有效性。
        
        Args:
            settings: settings["tags"][i] 字典，必须包含 "name"
            scenario_version: scenario 的版本（从 scenario 配置中获取）
        
        Returns:
            TagModel: 返回自身（支持链式调用）
        """
        if not TagModel.is_setting_valid(tag_setting, scenario_version):
            raise ValueError("Settings is not valid")
        
        # # 设置必需字段
        instance = cls(tag_setting, scenario_version)
        return instance

    @staticmethod
    def is_setting_valid(tag_setting: Dict[str, Any], scenario_version: str) -> bool:
        """
        验证 tag_setting 字典是否有效（静态方法，在创建实例前验证）
        
        Args:
            tag_setting: tag_setting["tags"][i] 字典
        
        Returns:
            bool: tag_setting 是否有效
        """
        if not tag_setting:
            logger.debug(f"当前tag_setting字典为空")
            return False
        
        if tag_setting.get("name") is None or not tag_setting.get("name"):
            logger.debug(f"当前tag_setting字典内缺少必要字段: name")
            return False
        
        if scenario_version is None or not scenario_version:
            logger.debug(f"当前传入的 scenario_version 字符串为空值")
            return False
        
        return True

    def get_name(self) -> str:
        return self.tag_name
    
    def get_settings(self) -> Dict[str, Any]:
        return self._settings

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'tag_name': self.tag_name,
            'scenario_id': self.scenario_id,
            'scenario_version': self.scenario_version,
            'display_name': self.display_name,
            'description': self.description,
            'is_legacy': self.is_legacy,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def ensure_metadata(self):
        """
        确保元信息存在
        """
        pass

    # ================================================================
    # Private implementations
    # ================================================================
    def _fill_in_default_values_to_settings(self, tag_setting: Dict[str, Any]) -> Dict[str, Any]:
        """
        填充默认值到settings字典中
        """
        pass

    def _set_values_from_settings(self, tag_setting: Dict[str, Any]) -> 'TagModel':
        """
        从 settings 字典配置当前实例
        """
        self.tag_name = tag_setting["name"]
        self.display_name = tag_setting.get("display_name") or self.tag_name  # 如果没有则使用 tag_name
        self.description = tag_setting.get("description") or ""  # 如果没有则为空字符串
        self.is_legacy = False  # 默认值

        self._is_configured = True
        self._is_ensured = False
        return self

   
    # @classmethod
    # def from_dict(cls, data: Dict[str, Any]) -> 'TagModel':
    #     """
    #     从字典创建 Model（通常是从数据库加载）
        
    #     Args:
    #         data: 数据库记录字典
        
    #     Returns:
    #         TagModel: 完整的 Model（所有字段都有值）
    #     """
    #     instance = cls()
    #     instance.id = data.get('id')
    #     instance.tag_name = data.get('tag_name', '')
    #     instance.scenario_id = data.get('scenario_id')
    #     instance.scenario_version = data.get('scenario_version', '')
    #     instance.display_name = data.get('display_name', '')
    #     instance.description = data.get('description', '')
    #     instance.is_legacy = bool(data.get('is_legacy', 0))
    #     instance.created_at = data.get('created_at')
    #     instance.updated_at = data.get('updated_at')
        
    #     # 标记状态
    #     instance._is_configured = True
    #     instance._is_ensured = True  # 从数据库加载的是完整的
        
    #     return instance