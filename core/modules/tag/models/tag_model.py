from typing import Dict, Any, List, Optional
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


class TagModel:
    """
    Tag Model (Tag Definition Model)
    
    使用流程：
    1. 创建实例：tag = TagModel()
    2. 从 settings 配置：tag.create_from_settings(settings["tags"][i])
    3. ensure_metadata 后：tag 完整（所有字段都有值）
    
    注意：
    - 在 ensure_metadata 之前，Model 可以是不完整的（ID=None, scenario_id=None, created_at=None 等）
    - 在 ensure_metadata 之后，Model 必须是完整的（所有字段都有值）
    """

    def __init__(self, tag_setting: Dict[str, Any]):
        """初始化 TagModel（所有字段为 None/False）"""
        self.id = None
        self.tag_name = None
        self.scenario_id = None
        self.display_name = None
        self.description = None
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
    def create_from_settings(cls, tag_setting: Dict[str, Any]) -> 'TagModel':
        """
        从 settings 字典配置当前实例
        
        用于在 ensure_metadata 之前从 settings 创建配置 Model。
        
        Args:
            tag_setting: settings["tags"][i] 字典，必须包含 "name"
        
        Returns:
            TagModel: 返回实例
        """
        if not TagModel.is_setting_valid(tag_setting):
            raise ValueError("Settings is not valid")
        
        instance = cls(tag_setting)
        return instance

    @classmethod
    def from_dict(cls, tag_dict: Dict[str, Any]) -> 'TagModel':
        """
        从字典创建 TagModel 实例（用于从数据库加载或从 to_dict() 恢复）
        
        Args:
            tag_dict: Tag 字典，包含：
                - id: int
                - tag_name: str
                - scenario_id: int
                - display_name: str
                - description: str
                - created_at: datetime
                - updated_at: datetime
        
        Returns:
            TagModel: TagModel 实例
        """
        # 创建一个临时的 tag_setting 字典（用于初始化）
        # 注意：from_dict 用于从数据库加载，所以 tag_name 应该已经存在
        tag_setting = {
            "name": tag_dict.get("tag_name", ""),
            "display_name": tag_dict.get("display_name", ""),
            "description": tag_dict.get("description", "")
        }
        
        instance = cls(tag_setting)
        
        # 设置数据库字段
        instance.id = tag_dict.get("id")
        instance.scenario_id = tag_dict.get("scenario_id")
        instance.created_at = tag_dict.get("created_at")
        instance.updated_at = tag_dict.get("updated_at")
        
        # 标记为已确保（因为是从数据库加载的完整数据）
        instance._is_ensured = True
        
        return instance

    @staticmethod
    def is_setting_valid(tag_setting: Dict[str, Any]) -> bool:
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
            'display_name': self.display_name,
            'description': self.description,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    def ensure_metadata(self, tag_data_mgr, scenario_id: int, recompute: bool = False):
        """
        确保元信息存在
        
        简化逻辑：
        - 如果 recompute=True 或 tag 不存在：创建新的 tag
        - 如果 recompute=False 且 tag 存在：检查 diff 并更新（如果需要）
        
        Args:
            tag_data_mgr: TagDataManager 实例
            scenario_id: Scenario ID（从 ScenarioModel 传入）
            recompute: 是否强制重新计算（从 ScenarioModel 传入）
        """
        # 设置 scenario_id（在调用 save_tag/update_tag 前必须设置）
        self.scenario_id = scenario_id
        
        if recompute:
            # 强制重新计算：删除旧的 tag（如果存在）并创建新的
            existing_tag = tag_data_mgr.load(self.tag_name, scenario_id)
            if existing_tag:
                # 删除旧的 tag definition（tag values 会在 scenario 级别删除）
                tag_data_mgr.delete_tag_definition(existing_tag.get('id'))
            
            # 创建新的 tag
            new_meta = tag_data_mgr.save(
                self.tag_name,
                scenario_id,
                self.display_name,
                self.description
            )
            self._set_meta(new_meta)
        else:
            # 检查 tag 是否存在
            existing_tag = tag_data_mgr.load(self.tag_name, scenario_id)
            
            if not existing_tag:
                # tag 不存在，创建新的
                new_meta = tag_data_mgr.save(
                    self.tag_name,
                    scenario_id,
                    self.display_name,
                    self.description
                )
                self._set_meta(new_meta)
            else:
                # tag 存在，检查是否有差异
                if self._has_meta_diff(existing_tag):
                    # 有差异，需要更新
                    new_meta = tag_data_mgr.update_tag_definition(
                        existing_tag.get('id'),
                        display_name=self.display_name,
                        description=self.description,
                        current_tag=existing_tag
                    )
                    self._set_meta(new_meta)
                else:
                    # 无差异，直接加载现有 metadata（不更新）
                    self._set_meta(existing_tag)



        self._is_ensured = True

    # ================================================================
    # Private implementations
    # ================================================================
    def _set_meta(self, new_meta: Dict[str, Any]):
        """
        设置 meta
        
        Args:
            new_meta: 包含完整数据库字段的字典
        """
        self.id = new_meta.get('id')
        self.scenario_id = new_meta.get('scenario_id')  # 确保 scenario_id 也被设置
        self.display_name = new_meta.get('display_name')
        self.description = new_meta.get('description')
        self.created_at = new_meta.get('created_at')
        self.updated_at = new_meta.get('updated_at')


    def _has_meta_diff(self, db_meta: Dict[str, Any]) -> bool:
        """
        比较 meta 差异
        
        Args:
            db_meta: 数据库中的 tag metadata 字典
        
        Returns:
            bool: 如果有差异返回 True，否则返回 False
        """
        # 比较 display_name 和 description 是否有变化
        if self.display_name != db_meta.get('display_name'):
            return True
        if self.description != db_meta.get('description'):
            return True
        return False

    def _fill_in_default_values_to_settings(self, tag_setting: Dict[str, Any]) -> Dict[str, Any]:
        """
        填充默认值到settings字典中
        
        根据 example_settings.py 的结构，填充所有可选字段的默认值。
        
        Args:
            tag_setting: 原始 tag_setting 字典（已通过验证）
            
        Returns:
            Dict[str, Any]: 填充了默认值的 tag_setting 字典
        """
        # 创建 tag_setting 的副本，避免修改原始字典
        filled_tag_setting = tag_setting.copy()
        
        # display_name: 如果没有则使用 name（在 _set_values_from_settings 中处理，这里不需要）
        # description: 默认空字符串（在 _set_values_from_settings 中处理，这里不需要）
        # 但为了保持 settings 完整，确保这些字段存在
        if "display_name" not in filled_tag_setting:
            filled_tag_setting["display_name"] = filled_tag_setting.get("name", "")
        
        if "description" not in filled_tag_setting:
            filled_tag_setting["description"] = ""
        
        return filled_tag_setting

    def _set_values_from_settings(self, tag_setting: Dict[str, Any]) -> 'TagModel':
        """
        从 settings 字典配置当前实例
        """
        self.tag_name = tag_setting["name"]
        self.display_name = tag_setting.get("display_name") or self.tag_name  # 如果没有则使用 tag_name
        self.description = tag_setting.get("description") or ""  # 如果没有则为空字符串

        self._is_configured = True
        self._is_ensured = False
        return self