from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from app.tag.core.config import ALLOW_VERSION_ROLLBACK, MAX_LEGACY_VERSIONS
from app.tag.core.enums import EnsureMetaAction, VersionChangeAction
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
        self._meta_action = None

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

    def ensure_metadata(self, tag_data_mgr):
        """
        确保元信息存在
        
        Returns:
            Tuple[str, str]: (start_date, end_date) 计算日期范围
        """
        self._ensure_scenario_metadata(tag_data_mgr)
        self._ensure_tags_metadata(tag_data_mgr, self._meta_action)
        self._is_ensured = True
        
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

    def _ensure_tags_metadata(self, tag_data_mgr, meta_action):
        """
        确保 tags 元信息存在
        
        Args:
            tag_data_mgr: TagDataManager 实例
            meta_action: EnsureMetaAction 枚举值
        """
        for tag_model in self._tag_models:
            # 传入 scenario_id 作为参数
            tag_model.ensure_metadata(tag_data_mgr, meta_action, self.id)

    def _ensure_scenario_metadata(self, tag_data_mgr):
        """
        确保 scenario 元信息存在
        """
        # 使用 TagDataService 的 load_scenario 方法
        scenario_metadata = tag_data_mgr.load_scenario(self.name, self.version)
        
        if not scenario_metadata:
            # 首次创建 scenario
            self._meta_action = EnsureMetaAction.NEW_SCENARIO.value
            # TODO: 修复 API 调用方式，使用正确的参数
            # new_meta = tag_data_mgr.save_scenario(
            #     self.name,
            #     self.version,
            #     display_name=self.display_name,
            #     description=self.description
            # )
            new_meta = tag_data_mgr.save_scenario(self.to_dict())  # 伪代码，待修复
            self._set_meta(new_meta)
            self._clear_legacy_scenarios_and_tags(tag_data_mgr)
        else:
            # scenario_metadata 是字典，使用字典访问
            if scenario_metadata.get('is_legacy', 0) == 1:
                # 版本回退
                if self._should_rollback():
                    self._meta_action = EnsureMetaAction.ROLLBACK.value
                    # TODO: 修复 API 调用方式，使用正确的参数
                    # new_meta = tag_data_mgr.update_scenario(
                    #     scenario_metadata.get('id'),
                    #     is_legacy=0,  # 激活当前版本
                    #     display_name=self.display_name,
                    #     description=self.description,
                    #     current_scenario=scenario_metadata
                    # )
                    new_meta = tag_data_mgr.update_scenario(self.to_dict())  # 伪代码，待修复
                    self._set_meta(new_meta)
                else:
                    self._meta_action = EnsureMetaAction.NO_CHANGE.value
            else:
                # 更新 scenario 元信息
                # 如果 version 没有变化，则更新 scenario 元信息
                if self._has_meta_diff(scenario_metadata):
                    self._meta_action = EnsureMetaAction.META_UPDATE.value
                    # TODO: 修复 API 调用方式，使用正确的参数
                    # new_meta = tag_data_mgr.update_scenario(
                    #     scenario_metadata.get('id'),
                    #     display_name=self.display_name,
                    #     description=self.description,
                    #     current_scenario=scenario_metadata
                    # )
                    new_meta = tag_data_mgr.update_scenario(self.to_dict())  # 伪代码，待修复
                    self._set_meta(new_meta)
                else:
                    self._meta_action = EnsureMetaAction.NO_CHANGE.value

    def _set_meta(self, new_meta: Dict[str, Any]):
        """
        设置 meta
        
        Args:
            new_meta: 包含完整数据库字段的字典
        """
        self.id = new_meta.get('id')
        self.display_name = new_meta.get('display_name')
        self.description = new_meta.get('description')
        self.is_legacy = bool(new_meta.get('is_legacy', 0))
        self.created_at = new_meta.get('created_at')
        self.updated_at = new_meta.get('updated_at')

    def _clear_legacy_scenarios_and_tags(self, tag_data_mgr):
        """
        清理 legacy scenarios
        """
        logger.info(f"检测到需要创建一个新的场景版本, 场景名称: {self.name}, 场景版本: {self.version}")
        logger.info(f"请注意如果当前场景的不同版本数量超过{MAX_LEGACY_VERSIONS}个，最老的场景版本和所产生的tags都将被删除。"
                    f"如果想修改这个限制，请在tag/core/config.py手动修改设置 MAX_LEGACY_VERSIONS={MAX_LEGACY_VERSIONS}。")
        tag_data_mgr.clear_legacy_scenarios_and_tags(self.name, MAX_LEGACY_VERSIONS)


    def _has_meta_diff(self, db_meta: Dict[str, Any]) -> bool:
        """
        比较 meta 差异
        
        Args:
            db_meta: 数据库中的 scenario metadata 字典
        
        Returns:
            bool: 如果有差异返回 True，否则返回 False
        """
        # TODO: 伪代码，待完善
        # 比较 display_name 和 description 是否有变化
        if self.display_name != db_meta.get('display_name'):
            return True
        if self.description != db_meta.get('description'):
            return True
        return False


    def _should_rollback(self):
        """
        处理版本回退
        """
        warning_msg = (
            f"请注意您的当前配置中的版本信息已经存在，信息如下："
            f"scenario={self.name}, version={self.version}. "
            "如果您是想会退版本，仅仅修改配置中的版本号到老版本是不够的，您还需要确保计算逻辑(tag worker中的代码逻辑)也已回退。"
        )
        action_msg = (
            f"当前回退行为已经被系统默认阻止。如果逻辑和版本号不匹配，计算的tag很可能不准确。"
            "如果您已经确认逻辑已经会退或者想继续执行，请在tag/core/config.py手动修改设置 ALLOW_VERSION_ROLLBACK=True 允许回退。"
        )

        logger.warning(warning_msg)

        if ALLOW_VERSION_ROLLBACK:
            return True

        logger.warning(action_msg)
        return False

        # str: VersionAction ("NO_CHANGE", "ROLLBACK", "NEW_SCENARIO", "REFRESH_SCENARIO")