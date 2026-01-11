"""
系统缓存 Model

适配实际表结构：id (int, auto_increment), value (text)
使用固定的 id 来标识不同的系统缓存项，value 字段直接存储值
"""
from typing import List, Dict, Any, Optional
from app.core.infra.db import DbBaseModel
from loguru import logger


class SystemCacheModel(DbBaseModel):
    """系统缓存 Model
    
    实际表结构：id (int, auto_increment), value (text)
    使用固定的 id 来标识不同的系统缓存项：
    - id=1: corporate_finance_batch_offset
    - 未来可以扩展：id=2, id=3 等对应其他用途
    """
    
    # 预定义的系统缓存项 ID 映射
    CACHE_IDS = {
        'corporate_finance_batch_offset': 1,
        # 未来可以添加更多映射
    }
    
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
        cache_id = self.CACHE_IDS.get(key)
        if not cache_id:
            logger.warning(f"未知的系统缓存键: {key}")
            return None
        
        try:
            record = self.load_one("id = %s", (cache_id,))
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
        cache_id = self.CACHE_IDS.get(key)
        if not cache_id:
            logger.warning(f"未知的系统缓存键: {key}")
            return 0
        
        try:
            # 检查记录是否存在
            existing = self.load_one("id = %s", (cache_id,))
            if existing:
                # 更新现有记录
                return self.update({'value': value}, "id = %s", (cache_id,))
            else:
                # 插入新记录（需要指定 id）
                # 注意：由于 id 是 auto_increment，我们需要手动插入指定 id
                with self.db.get_sync_cursor() as cursor:
                    cursor.execute(
                        f"INSERT INTO {self.table_name} (id, value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE value = %s",
                        (cache_id, value, value)
                    )
                    cursor.connection.commit()
                    return 1
        except Exception as e:
            logger.error(f"保存系统缓存失败: {e}")
            return 0
    
    def delete_by_key(self, key: str) -> int:
        """删除指定key的系统缓存"""
        cache_id = self.CACHE_IDS.get(key)
        if not cache_id:
            logger.warning(f"未知的系统缓存键: {key}")
            return 0
        
        try:
            return self.delete("id = %s", (cache_id,))
        except Exception as e:
            logger.error(f"删除系统缓存失败: {e}")
            return 0


__all__ = ['SystemCacheModel']
