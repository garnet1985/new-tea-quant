from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from app.tag.core.enums import EnsureMetaAction


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

    def ensure_metadata(self, tag_data_mgr, meta_action, scenario_id: int):
        """
        确保元信息存在
        
        逻辑：
        - NEW_SCENARIO: 直接 save_tag（tag 不存在）
        - 其他情况（META_UPDATE, ROLLBACK, NO_CHANGE）: 统一处理为 load → diff → update
        
        Args:
            tag_data_mgr: TagDataManager 实例
            meta_action: EnsureMetaAction 枚举值
            scenario_id: Scenario ID（从 ScenarioModel 传入）
        """
        # 设置 scenario_id（在调用 save_tag/update_tag 前必须设置）
        self.scenario_id = scenario_id
        
        if meta_action == EnsureMetaAction.NEW_SCENARIO.value:
            # 首次创建 tag（scenario 不存在，所以 tag 也不存在）
            # TODO: 修复 API 调用方式，使用正确的参数
            # new_meta = tag_data_mgr.save_tag(
            #     self.tag_name,
            #     scenario_id,
            #     self.scenario_version,
            #     self.display_name,
            #     self.description
            # )
            new_meta = tag_data_mgr.save_tag(self.to_dict())  # 伪代码，待修复
            self._set_meta(new_meta)
        else:
            # 其他情况（META_UPDATE, ROLLBACK, NO_CHANGE）统一处理：
            # scenario 已存在，所以 tag 也应该已存在，只需要检查 diff 并 update
            existing_tag = tag_data_mgr.load_tag(
                self.tag_name, 
                scenario_id, 
                self.scenario_version
            )
            
            if not existing_tag:
                # 不应该发生（scenario 存在但 tag 不存在），但为了安全还是创建
                logger.warning(
                    f"Tag 不存在但 scenario 已存在: "
                    f"tag_name={self.tag_name}, scenario_id={scenario_id}, "
                    f"meta_action={meta_action}"
                )
                # TODO: 修复 API 调用方式
                new_meta = tag_data_mgr.save_tag(self.to_dict())  # 伪代码，待修复
                self._set_meta(new_meta)
            else:
                # 检查是否有差异
                if self._has_meta_diff(existing_tag):
                    # 有差异，需要更新
                    # TODO: 修复 API 调用方式，使用正确的参数
                    # new_meta = tag_data_mgr.update_tag_definition(
                    #     existing_tag.get('id'),
                    #     display_name=self.display_name,
                    #     description=self.description,
                    #     current_tag=existing_tag
                    # )
                    new_meta = tag_data_mgr.update_tag(self.to_dict())  # 伪代码，待修复
                    self._set_meta(new_meta)
                else:
                    # 无差异，直接加载现有 metadata（不更新）
                    self._set_meta(existing_tag)



        self._is_ensured = True

    # ================================================================
    # Private implementations
    # ================================================================
    def _set_meta(self, new_meta):
        """
        设置 meta
        """
        self.id = new_meta.id
        self.display_name = new_meta.display_name
        self.description = new_meta.description
        self.is_legacy = new_meta.is_legacy
        self.created_at = new_meta.created_at
        self.updated_at = new_meta.updated_at


    def _has_meta_diff(self, db_meta: Dict[str, Any]) -> bool:
        """
        比较 meta 差异
        
        Args:
            db_meta: 数据库中的 tag metadata 字典
        
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