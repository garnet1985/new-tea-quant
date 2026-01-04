"""
Tag Scenario Model - 业务场景表
"""
from typing import List, Dict, Any, Optional
from app.core.infra.db import DbBaseModel
from loguru import logger


class TagScenarioModel(DbBaseModel):
    """Tag Scenario Model"""
    
    def __init__(self, db=None):
        super().__init__('tag_scenario', db)
    
    def load_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        根据名称查询 scenario
        
        Args:
            name: Scenario 名称
            
        Returns:
            Dict 或 None
        """
        return self.load_one("name = %s", (name,))
    
    def load_all(self) -> List[Dict[str, Any]]:
        """
        查询所有 scenarios
        
        Returns:
            List[Dict]: Scenario 列表
        """
        return self.load("1=1", order_by="name ASC, created_at DESC")
    
    def save_scenario(self, scenario_data: Dict[str, Any]) -> int:
        """
        保存 scenario（自动去重）
        
        Args:
            scenario_data: Scenario 数据字典，包含：
                - name: str
                - display_name: str (可选)
                - description: str (可选)
        
        Returns:
            int: 保存的记录数（通常是 1）
        """
        return self.replace_one(
            scenario_data,
            unique_keys=['name']
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
    
    def delete_scenario(self, scenario_id: int) -> int:
        """
        删除 scenario
        
        Args:
            scenario_id: Scenario ID
        
        Returns:
            int: 删除的记录数（通常是 1）
        """
        return self.delete("id = %s", (scenario_id,))
