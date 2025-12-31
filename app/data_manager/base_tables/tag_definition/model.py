"""
Tag Definition Model - 标签定义表
"""
from typing import List, Dict, Any, Optional
from utils.db import DbBaseModel
from loguru import logger


class TagDefinitionModel(DbBaseModel):
    """Tag Definition Model"""
    
    def __init__(self, db=None):
        super().__init__('tag_definition', db)
    
    def load_by_name_and_scenario(self, name: str, scenario_id: int, scenario_version: str) -> Optional[Dict[str, Any]]:
        """
        根据名称、scenario_id 和 scenario_version 查询 tag definition
        
        Args:
            name: Tag 名称
            scenario_id: Scenario ID
            scenario_version: Scenario 版本
            
        Returns:
            Dict 或 None
        """
        return self.load_one(
            "name = %s AND scenario_id = %s AND scenario_version = %s",
            (name, scenario_id, scenario_version)
        )
    
    def load_by_scenario_id(self, scenario_id: int, include_legacy: bool = False) -> List[Dict[str, Any]]:
        """
        根据 scenario_id 查询所有 tag definitions
        
        Args:
            scenario_id: Scenario ID
            include_legacy: 是否包含 legacy tags（默认 False）
            
        Returns:
            List[Dict]: Tag definition 列表
        """
        if include_legacy:
            return self.load("scenario_id = %s", (scenario_id,), order_by="name ASC")
        else:
            return self.load(
                "scenario_id = %s AND is_legacy = 0",
                (scenario_id,),
                order_by="name ASC"
            )
    
    def save_tag_definition(self, tag_data: Dict[str, Any]) -> int:
        """
        保存 tag definition（自动去重）
        
        Args:
            tag_data: Tag definition 数据字典，包含：
                - scenario_id: int
                - scenario_version: str
                - name: str
                - display_name: str
                - description: str (可选)
                - is_legacy: int (可选，默认 0)
        
        Returns:
            int: 保存的记录数（通常是 1）
        """
        # 设置默认值
        if 'is_legacy' not in tag_data:
            tag_data['is_legacy'] = 0
        
        return self.replace_one(
            tag_data,
            unique_keys=['scenario_id', 'name']
        )
    
    def delete_by_scenario_id(self, scenario_id: int) -> int:
        """
        删除指定 scenario 下的所有 tag definitions
        
        Args:
            scenario_id: Scenario ID
        
        Returns:
            int: 删除的记录数
        """
        return self.delete("scenario_id = %s", (scenario_id,))
