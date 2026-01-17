from typing import Any, Dict, List, Optional
from datetime import datetime
from loguru import logger

from core.infra.project_context import ConfigManager
from core.modules.tag.core.enums import TagUpdateMode
from core.modules.tag.core.models.tag_model import TagModel


class ScenarioModel:
    """
    Scenario Model
    
    使用流程：
    1. 创建实例：scenario = ScenarioModel()
    2. 从 settings 配置：scenario.create_from_settings(settings)
    3. ensure_metadata 后：scenario 完整（所有字段都有值）
    
    注意：
    - 在 ensure_metadata 之前，Model 可以是不完整的（ID=None, created_at=None 等）
    - 在 ensure_metadata 之后，Model 必须是完整的（所有字段都有值）
    """

    def __init__(self, settings: Dict[str, Any]):
        """初始化 ScenarioModel（所有字段为 None/False）"""
        self.id = None
        self.name = None
        self.display_name = None
        self.description = None
        self.created_at = None
        self.updated_at = None
        
        # 状态标记
        self._is_configured = False  # 是否已从 settings 配置
        self._is_ensured = False  # 是否已 ensure_metadata（完整）
        self._is_enabled = False
        self._recompute = False  # 是否强制重新计算

        # 其他字段
        self._target_entity = None
        
        # 先填充默认值，然后从 settings 设置值
        self._settings = self._fill_in_default_values_to_settings(settings)
        self._set_values_from_setting(self._settings)
        
        # tagModel列表（在设置值之后）
        self._tag_models = self._cache_tag_models(self._settings)


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
        """获取 scenario 标识符（name）"""
        return self.name

    def should_recompute(self) -> bool:
        """是否应该强制重新计算"""
        return self._recompute

    def ensure_metadata(self, tag_data_mgr):
        """
        确保元信息存在
        
        简化逻辑：
        - 如果 scenario 不存在：创建新的
        - 如果 scenario 存在且 recompute=True：删除旧的 scenario 和 tags，创建新的
        - 如果 scenario 存在且 recompute=False：检查 meta 差异并更新（如果需要）
        """
        self._ensure_scenario_metadata(tag_data_mgr)
        self._ensure_tags_metadata(tag_data_mgr)
        self._is_ensured = True

    def calculate_update_mode(self) -> TagUpdateMode:
        """
        计算更新模式
        
        Returns:
            TagUpdateMode: Tag 系统更新模式枚举
        """
        if self._recompute:
            return TagUpdateMode.REFRESH
        
        # 从 settings 中获取 update_mode（新结构：直接在顶层或 performance.update_mode）
        # 优先从顶层获取，如果没有则从 performance 获取
        update_mode_str = self._settings.get("update_mode")
        if not update_mode_str:
            performance = self._settings.get("performance", {})
            update_mode_str = performance.get("update_mode", "incremental")
        
        # 转换为 TagUpdateMode 枚举
        try:
            return TagUpdateMode(update_mode_str)
        except ValueError:
            logger.warning(f"无效的 update_mode: {update_mode_str}，使用默认值 INCREMENTAL")
            return TagUpdateMode.INCREMENTAL
        
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

        # name 已经在发现场景时验证过了
        scenario_name = settings.get("name")
        
        if settings.get("target_entity") is None or not settings.get("target_entity"):
            logger.debug(f"当前传入的{scenario_name} settings缺少属性: target_entity")
            return False

        if settings.get("is_enabled") is None:
            logger.debug(f"当前传入的settings缺少属性: is_enabled, 默认设置为False")
            settings["is_enabled"] = False

        # recompute 字段可选，默认为 False
        if settings.get("recompute") is None:
            settings["recompute"] = False

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
        
        # 验证 incremental_required_records_before_as_of_date
        # 如果 update_mode == INCREMENTAL，必须显式声明此配置
        update_mode_str = settings.get("update_mode")
        if not update_mode_str:
            performance = settings.get("performance", {})
            update_mode_str = performance.get("update_mode", "incremental")
        
        try:
            update_mode = TagUpdateMode(update_mode_str)
            if update_mode == TagUpdateMode.INCREMENTAL:
                # INCREMENTAL 模式下，必须显式声明 incremental_required_records_before_as_of_date
                if "incremental_required_records_before_as_of_date" not in settings:
                    logger.error(f"当前传入的{scenario_name} settings在INCREMENTAL模式下缺少必须参数: incremental_required_records_before_as_of_date")
                    return False
                # 验证值是否为非负整数
                required_records = settings.get("incremental_required_records_before_as_of_date")
                if not isinstance(required_records, int) or required_records < 0:
                    logger.error(f"当前传入的{scenario_name} settings的incremental_required_records_before_as_of_date必须是非负整数，当前值: {required_records}")
                    return False
        except ValueError:
            # update_mode 无效，但这里不验证（会在其他地方处理）
            pass
        
        return True


    # ================================================================
    # Private implementations
    # ================================================================
    def _set_values_from_setting(self, scenario_setting: Dict[str, Any]):
        # 设置必需字段
        self.name = scenario_setting["name"]
        
        # 设置 target_entity（从 target_entity.type 获取）
        target_entity_config = scenario_setting.get("target_entity", {})
        if isinstance(target_entity_config, dict):
            self._target_entity = target_entity_config.get("type")
        else:
            # 如果 target_entity 是字符串（旧格式），直接使用
            self._target_entity = target_entity_config
        
        # 设置可选字段（有默认值）
        self.display_name = scenario_setting.get("display_name") or self.name  # 如果没有则使用 name
        self.description = scenario_setting.get("description") or ""  # 如果没有则为空字符串
        # id, created_at, updated_at 保持为 None
        
        # 标记已配置
        self._is_configured = True
        self._is_ensured = False
        self._is_enabled = scenario_setting.get("is_enabled", False)  # 从 settings 读取 is_enabled
        self._recompute = scenario_setting.get("recompute", False)  # 从 settings 读取 recompute

        self._tags = []
        
        return self

    def _fill_in_default_values_to_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        填充默认值到settings字典中
        
        根据 example_settings.py 的结构，填充所有可选字段的默认值。
        
        Args:
            settings: 原始 settings 字典（已通过验证）
            
        Returns:
            Dict[str, Any]: 填充了默认值的 settings 字典
        """
        # 创建 settings 的副本，避免修改原始字典
        filled_settings = settings.copy()
        
        # Scenario 级别可选字段（顶层）
        # display_name: 如果没有则使用 name（在 _set_values_from_setting 中处理，这里不需要）
        # description: 默认空字符串（在 _set_values_from_setting 中处理，这里不需要）
        # start_date: 默认使用系统默认开始日期
        if "start_date" not in filled_settings or filled_settings.get("start_date") == "":
            filled_settings["start_date"] = ConfigManager.get_default_start_date()
        
        # end_date: 默认使用最新已完成交易日
        if "end_date" not in filled_settings or filled_settings.get("end_date") == "":
            # 从 DataManager 获取最新已完成交易日（单例模式）
            try:
                from core.modules.data_manager import DataManager
                data_mgr = DataManager(is_verbose=False)
                filled_settings["end_date"] = data_mgr.service.calendar.get_latest_completed_trading_date()
            except Exception as e:
                logger.warning(f"获取最新交易日失败，使用空字符串: {e}")
                filled_settings["end_date"] = ""
        
        # required_entities: 默认空列表 []
        if "required_entities" not in filled_settings:
            filled_settings["required_entities"] = []
        

        # calculator.performance: 确保存在
        if "performance" not in filled_settings:
            filled_settings["performance"] = {}
        
        performance = filled_settings["performance"]
        # calculator.performance.update_mode: 默认 "incremental"
        if "update_mode" not in performance:
            performance["update_mode"] = "incremental"
        
        # calculator.performance.max_workers: 默认 "auto"
        if "max_workers" not in performance:
            performance["max_workers"] = "auto"
        
        # calculator.performance.data_chunk_size: 默认 500
        if "data_chunk_size" not in performance:
            performance["data_chunk_size"] = 500
        
        # tags: 必须字段，不需要默认值（已在验证中检查）
        # 但需要为每个 tag 填充默认值（在 TagModel 中处理）
        
        return filled_settings

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    

    def _cache_tag_models(self, settings: Dict[str, Any]) -> List[TagModel]:
        """
        缓存 tag_models
        """
        tag_models = []
        for tag_setting in settings["tags"]:
            tag_model = TagModel.create_from_settings(tag_setting)
            tag_models.append(tag_model)
            
        return tag_models

    def _ensure_tags_metadata(self, tag_data_mgr):
        """
        确保 tags 元信息存在
        
        Args:
            tag_data_mgr: TagDataManager 实例
        """
        for tag_model in self._tag_models:
            # 传入 scenario_id 作为参数
            tag_model.ensure_metadata(tag_data_mgr, self.id, self._recompute)

    def _ensure_scenario_metadata(self, tag_data_mgr):
        """
        确保 scenario 元信息存在
        
        简化逻辑：
        - 如果 scenario 不存在：创建新的
        - 如果 scenario 存在且 recompute=True：删除旧的 scenario 和 tags，创建新的
        - 如果 scenario 存在且 update_mode=REFRESH：删除 tag values（保留 scenario 和 tag definitions）
        - 如果 scenario 存在且 recompute=False：检查 meta 差异并更新（如果需要）
        """
        # 使用 TagDataService 的 load_scenario 方法（只按 name 查询）
        scenario_metadata = tag_data_mgr.load_scenario(self.name)
        
        if not scenario_metadata:
            # 首次创建 scenario
            new_meta = tag_data_mgr.save_scenario(
                self.name,
                display_name=self.display_name,
                description=self.description
            )
            self._set_meta(new_meta)
        else:
            # scenario 已存在
            scenario_id = scenario_metadata.get('id')
            
            if self._recompute:
                # 强制重新计算：删除旧的 scenario 和 tags
                logger.info(f"检测到 recompute=True，删除旧的 scenario 和 tags: {self.name}")
                
                # 删除 tag values
                tag_data_mgr.delete_tag_values_by_scenario(scenario_id)
                # 删除 tag definitions
                tag_data_mgr.delete_tag_definitions_by_scenario(scenario_id)
                # 删除 scenario
                tag_data_mgr.delete_scenario(scenario_id, cascade=False)
                
                # 创建新的 scenario
                new_meta = tag_data_mgr.save_scenario(
                    self.name,
                    display_name=self.display_name,
                    description=self.description
                )
                self._set_meta(new_meta)
            else:
                # 检查 update_mode，如果是 REFRESH 模式，删除 tag values
                update_mode = self.calculate_update_mode()
                if update_mode == TagUpdateMode.REFRESH:
                    logger.info(f"检测到 update_mode=REFRESH，删除旧的 tag values: {self.name}")
                    # 只删除 tag values，保留 scenario 和 tag definitions
                    tag_data_mgr.delete_tag_values_by_scenario(scenario_id)
                
                # 检查 meta 差异并更新（如果需要）
                if self._has_meta_diff(scenario_metadata):
                    new_meta = tag_data_mgr.update_scenario(
                        scenario_metadata.get('id'),
                        display_name=self.display_name,
                        description=self.description,
                        current_scenario=scenario_metadata
                    )
                    self._set_meta(new_meta)
                else:
                    # 无差异，直接加载现有 metadata
                    self._set_meta(scenario_metadata)

    def _set_meta(self, new_meta: Dict[str, Any]):
        """
        设置 meta
        
        Args:
            new_meta: 包含完整数据库字段的字典
        """
        self.id = new_meta.get('id')
        self.display_name = new_meta.get('display_name')
        self.description = new_meta.get('description')
        self.created_at = new_meta.get('created_at')
        self.updated_at = new_meta.get('updated_at')

    def _has_meta_diff(self, db_meta: Dict[str, Any]) -> bool:
        """
        比较 meta 差异
        
        Args:
            db_meta: 数据库中的 scenario metadata 字典
        
        Returns:
            bool: 如果有差异返回 True，否则返回 False
        """
        # 比较 display_name 和 description 是否有变化
        if self.display_name != db_meta.get('display_name'):
            return True
        if self.description != db_meta.get('description'):
            return True
        return False
