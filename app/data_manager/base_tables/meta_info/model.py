"""
元信息 Model
"""
from typing import List, Dict, Any, Optional
from utils.db.db_model import BaseTableModel


class MetaInfoModel(BaseTableModel):
    """元信息 Model"""
    
    def __init__(self, db):
        super().__init__('meta_info', db)
    
    def load_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """根据key查询元信息"""
        return self.load_one("key = %s", (key,))
    
    def load_all_meta(self) -> List[Dict[str, Any]]:
        """查询所有元信息"""
        return self.load("1=1", order_by="key ASC")
    
    def save_meta(self, key: str, value: str, description: str = None) -> int:
        """保存或更新元信息"""
        data = {'key': key, 'value': value}
        if description:
            data['description'] = description
        return self.replace([data], unique_keys=['key'])
    
    def delete_by_key(self, key: str) -> int:
        """删除指定key的元信息"""
        return self.delete("key = %s", (key,))

