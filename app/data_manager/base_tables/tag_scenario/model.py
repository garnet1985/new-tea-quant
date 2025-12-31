"""
Tag Scenario Model - 业务场景表
"""
from typing import List, Dict, Any, Optional
from utils.db import DbBaseModel
from loguru import logger


class TagScenarioModel(DbBaseModel):
    """Tag Scenario Model"""
    
    def __init__(self, db=None):
        super().__init__('tag_scenario', db)
    
    def load_by_name_and_version(self, name: str, version: str) -> Optional[Dict[str, Any]]:
        """
        根据名称和版本查询 scenario
        
        Args:
            name: Scenario 名称
            version: Scenario 版本
            
        Returns:
            Dict 或 None
        """
        return self.load_one("name = %s AND version = %s", (name, version))
    
    def load_by_name(self, name: str, include_legacy: bool = False) -> List[Dict[str, Any]]:
        """
        根据名称查询所有版本的 scenarios
        
        Args:
            name: Scenario 名称
            include_legacy: 是否包含 legacy 版本（默认 False）
            
        Returns:
            List[Dict]: Scenario 列表
        """
        if include_legacy:
            return self.load("name = %s", (name,), order_by="created_at DESC")
        else:
            return self.load("name = %s AND is_legacy = 0", (name,), order_by="created_at DESC")
    
    def load_all(self, include_legacy: bool = False) -> List[Dict[str, Any]]:
        """
        查询所有 scenarios
        
        Args:
            include_legacy: 是否包含 legacy 版本（默认 False）
            
        Returns:
            List[Dict]: Scenario 列表
        """
        if include_legacy:
            return self.load("1=1", order_by="name ASC, created_at DESC")
        else:
            return self.load("is_legacy = 0", order_by="name ASC, created_at DESC")
    
    def save_scenario(self, scenario_data: Dict[str, Any]) -> int:
        """
        保存 scenario（自动去重）
        
        Args:
            scenario_data: Scenario 数据字典，包含：
                - name: str
                - version: str
                - display_name: str (可选)
                - description: str (可选)
                - is_legacy: int (可选，默认 0)
        
        Returns:
            int: 保存的记录数（通常是 1）
        """
        # 设置默认值
        if 'is_legacy' not in scenario_data:
            scenario_data['is_legacy'] = 0
        
        return self.replace_one(
            scenario_data,
            unique_keys=['name', 'version']
        )
    
    def update_scenario(self, scenario_id: int, update_data: Dict[str, Any]) -> int:
        """
        更新 scenario
        
        Args:
            scenario_id: Scenario ID
            update_data: 要更新的字段字典
        
        Returns:
            int: 更新的记录数（通常是 1）
        """
        return self.update("id = %s", (scenario_id,), update_data)
    
    def mark_as_legacy(self, scenario_id: int) -> int:
        """
        将 scenario 标记为 legacy
        
        Args:
            scenario_id: Scenario ID
        
        Returns:
            int: 更新的记录数（通常是 1）
        """
        return self.update("id = %s", (scenario_id,), {'is_legacy': 1})
    
    def delete_scenario(self, scenario_id: int) -> int:
        """
        删除 scenario
        
        Args:
            scenario_id: Scenario ID
        
        Returns:
            int: 删除的记录数（通常是 1）
        """
        return self.delete("id = %s", (scenario_id,))
