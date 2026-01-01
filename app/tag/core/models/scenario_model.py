from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from app.tag.core.models.tag_model import TagModel


class ScenarioModel:
    """
    Scenario Model
    
    使用流程：
    1. 创建实例：scenario = ScenarioModel()
    2. 从 settings 配置：scenario.create_from_settings(settings["scenario"])
    3. 验证配置：scenario.is_valid()  # 验证配置字段（name, version）
    4. ensure_metadata 后：scenario.is_complete()  # 验证完整性（所有字段都有值）
    
    注意：
    - 在 ensure_metadata 之前，Model 可以是不完整的（ID=None, created_at=None 等）
    - 在 ensure_metadata 之后，Model 必须是完整的（所有字段都有值）
    """

    def __init__(self, settings: Dict[str, Any]):
        """初始化 ScenarioModel（所有字段为 None/False）"""
        self.id = None
        self.name = None
        self.version = None
        self.display_name = None
        self.description = None
        self.is_legacy = False
        self.created_at = None
        self.updated_at = None
        
        # 状态标记
        self._is_configured = False  # 是否已从 settings 配置
        self._is_ensured = False  # 是否已 ensure_metadata（完整）
        self._is_enabled = False

        # 其他字段
        self._target_entity = None
        # tagModel列表
        self._tag_models = self._cache_tag_models(settings)
        self._settings = self._fill_in_default_values_to_settings(settings)


    # ================================================================
    # Public APIs
    # ================================================================
    @classmethod
    def create_from_settings(cls, settings: Dict[str, Any]) -> 'ScenarioModel':
        """
        从 settings 字典配置当前实例
        """
        if not cls.is_setting_valid(settings):
            return None
        instance = cls(settings)
        return instance
        
    def is_enabled(self) -> bool:
        return self._is_enabled
    
    def get_target_entity(self) -> str:
        return self._target_entity
    
    def get_tag_models(self) -> List[TagModel]:
        return self._tag_models

    def get_tags_dict(self) -> Dict[str, TagModel]:
        tags_dict = {}
        for tag_model in self._tag_models:
            tags_dict[tag_model.get_name()] = tag_model.to_dict()
        return tags_dict

    def get_settings(self) -> Dict[str, Any]:
        return self._settings
    
    def get_name(self) -> str:
        return self.name

    def get_identifier(self) -> str:
        """获取 scenario 标识符（name:version）"""
        return f"{self.name}:{self.version}"

    def ensure_metadata(self):
        """
        确保元信息存在
        
        Returns:
            Tuple[str, str]: (start_date, end_date) 计算日期范围
        """
        self._ensure_scenario_metadata()
        self._ensure_tags_metadata()
        self._is_ensured = True
        
        # TODO: 伪代码，待完善
        # 确定计算日期范围（从 TagMetaManager 获取或从 settings 中读取）
        start_date = None  # 待实现
        end_date = None  # 待实现
        
        return start_date, end_date
    
    @staticmethod
    def is_setting_valid(settings: Dict[str, Any] = None) -> bool:
        """
        验证 settings 字典所有必须字段是不是都存在并且满足基本条件
        
        Args:
            settings: settings 字典
        
        Returns:
            bool: settings 是否有效
        """

        if not settings:
            logger.warning(f"传入的settings 为空")
            return False

        if settings.get("name") is None or not settings.get("name"):
            logger.debug(f"当前传入的settings内缺少必要字段: name")
            return False

        scenario_name = settings.get("name")
        if settings.get("version") is None or not settings.get("version"):
            logger.debug(f"当前传入的{scenario_name} settings缺少属性: version")
            return False
        
        if settings.get("target_entity") is None or not settings.get("target_entity"):
            logger.debug(f"当前传入的{scenario_name} settings缺少属性: target_entity")
            return False

        if settings.get("is_enabled") is None:
            logger.debug(f"当前传入的settings缺少属性: is_enabled, 默认设置为False")
            settings["is_enabled"] = False

        tags_setting = settings.get("tags", None)
        if not tags_setting:
            logger.debug(f"当前传入的{scenario_name} settings里缺少tags字段")
            return False

        if not isinstance(tags_setting, list):
            logger.debug(f"当前传入的{scenario_name} settings内的tags字段必须是列表类型")
            return False

        if len(tags_setting) == 0:
            logger.debug(f"当前传入的{scenario_name} settings内的tags字段必须至少包含一个 tag")
            return False
        
        return True


    # ================================================================
    # Private implementations
    # ================================================================
    def _set_values_from_setting(self, scenario_setting: Dict[str, Any]):
        # 设置必需字段
        self.name = scenario_setting["name"]
        self.version = scenario_setting["version"]
        
        # 设置可选字段（有默认值）
        self.display_name = scenario_setting.get("display_name") or self.name  # 如果没有则使用 name
        self.description = scenario_setting.get("description") or ""  # 如果没有则为空字符串
        self.is_legacy = False  # 默认值
        # id, created_at, updated_at 保持为 None
        
        # 标记已配置
        self._is_configured = True
        self._is_ensured = False
        self._is_enabled = scenario_setting.get("is_enabled", False)  # 从 settings 读取 is_enabled

        self._tags = []
        
        return self

    def _fill_in_default_values_to_settings(self, settings: Dict[str, Any]):
        """
        填充默认值到settings字典中
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'version': self.version,
            'display_name': self.display_name,
            'description': self.description,
            'is_legacy': self.is_legacy,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    

    def _cache_tag_models(self, settings: Dict[str, Any]) -> List[TagModel]:
        """
        缓存 tag_models
        """
        tag_models = []
        for tag_setting in settings["tags"]:
            tag_model = TagModel.create_from_settings(tag_setting, self.version)
            tag_models.append(tag_model)
            
        return tag_models

    

    def _ensure_scenario_metadata(self):
        """
        确保 scenario 元信息存在
        """
        pass

    def _ensure_tags_metadata(self):
        """
        确保 tags 元信息存在
        """
        for tag_model in self._tag_models:
            tag_model.ensure_metadata()


        