"""
Tag Model - 标签元信息
"""
from typing import List, Dict, Any, Optional
from utils.db import DbBaseModel


class TagModel(DbBaseModel):
    """标签元信息 Model"""
    
    def __init__(self, db=None):
        super().__init__('tag', db)
    
    def load_by_id(self, tag_id: int) -> Optional[Dict[str, Any]]:
        """根据标签ID查询"""
        return self.load_one("id = %s", (tag_id,))
    
    def load_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据标签名称（machine readable）查询"""
        return self.load_one("name = %s", (name,))
    
    def load_enabled_tags(self) -> List[Dict[str, Any]]:
        """查询所有启用的标签"""
        return self.load("is_enabled = 1", order_by="name ASC")
    
    def save_tag(self, tag_data: Dict[str, Any]) -> int:
        """保存标签（自动去重，基于 name）"""
        return self.replace_one(tag_data, unique_keys=['name'])
    
    def batch_save_tags(self, tags: List[Dict[str, Any]]) -> int:
        """批量保存标签（自动去重，基于 name）"""
        return self.replace(tags, unique_keys=['name'])
