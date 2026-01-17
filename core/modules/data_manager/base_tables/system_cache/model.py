"""
系统缓存 Model

适配实际表结构：key (varchar(100), PRIMARY KEY), value (varchar(255)), updated_at (datetime)
使用 key 字段直接存储缓存键名，value 字段存储缓存值
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel
from loguru import logger
from datetime import datetime


class SystemCacheModel(DbBaseModel):
    """系统缓存 Model
    
    实际表结构：key (varchar(100), PRIMARY KEY), value (varchar(255)), updated_at (datetime)
    使用 key 字段直接存储缓存键名（如 'corporate_finance_batch_offset'）
    """
    
    def __init__(self, db=None):
        super().__init__('system_cache', db)
    
    def load_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """
        根据key查询系统缓存
        
        Args:
            key: 缓存键（如 'corporate_finance_batch_offset'）
            
        Returns:
            Dict 包含 'value'，如果不存在返回 None
        """
        try:
            # key 是保留字，需要使用引号引用
            record = self.load_one('"key" = ?', (key,))
            if record:
                return {'value': record.get('value')}
            return None
        except Exception as e:
            logger.error(f"查询系统缓存失败: {e}")
            return None
    
    def save_cache(self, key: str, value: str) -> int:
        """
        保存或更新系统缓存
        
        Args:
            key: 缓存键（如 'corporate_finance_batch_offset'）
            value: 缓存值（直接存储在 value 字段）
            
        Returns:
            保存的记录数
        """
        try:
            # 使用 replace_one 实现 upsert（插入或更新）
            # unique_keys=['key'] 表示如果 key 已存在则更新，否则插入
            return self.replace_one(
                {
                    'key': key,
                    'value': value,
                    'updated_at': datetime.now()
                },
                unique_keys=['key']
            )
        except Exception as e:
            logger.error(f"保存系统缓存失败: {e}")
            return 0
    
    def delete_by_key(self, key: str) -> int:
        """删除指定key的系统缓存"""
        try:
            # key 是保留字，需要使用引号引用
            return self.delete('"key" = ?', (key,))
        except Exception as e:
            logger.error(f"删除系统缓存失败: {e}")
            return 0


__all__ = ['SystemCacheModel']
