"""
元信息 Model

适配实际表结构：id (int, auto_increment), info (text)
使用固定的 id 来标识不同的元信息项，info 字段直接存储值
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel
from loguru import logger


class MetaInfoModel(DbBaseModel):
    """元信息 Model
    
    实际表结构：id (int, auto_increment), info (text)
    使用固定的 id 来标识不同的元信息项：
    - id=1: corporate_finance_batch_offset
    - 未来可以扩展：id=2, id=3 等对应其他用途
    """
    
    # 预定义的元信息项 ID 映射
    META_IDS = {
        'corporate_finance_batch_offset': 1,
        # 未来可以添加更多映射
    }
    
    def __init__(self, db=None):
        super().__init__('meta_info', db)
    
    def load_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """
        根据key查询元信息
        
        Args:
            key: 元信息键（如 'corporate_finance_batch_offset'）
            
        Returns:
            Dict 包含 'value'，如果不存在返回 None
        """
        meta_id = self.META_IDS.get(key)
        if not meta_id:
            logger.warning(f"未知的元信息键: {key}")
            return None
        
        try:
            record = self.load_one("id = ?", (meta_id,))
            if record:
                return {'value': record.get('info')}
            return None
        except Exception as e:
            logger.error(f"查询元信息失败: {e}")
            return None
    
    def save_meta(self, key: str, value: str, description: str = None) -> int:
        """
        保存或更新元信息
        
        Args:
            key: 元信息键（如 'corporate_finance_batch_offset'）
            value: 元信息值（直接存储在 info 字段）
            description: 元信息描述（可选，当前不使用）
            
        Returns:
            保存的记录数
        """
        meta_id = self.META_IDS.get(key)
        if not meta_id:
            logger.warning(f"未知的元信息键: {key}")
            return 0
        
        try:
            # 检查记录是否存在
            existing = self.load_one("id = ?", (meta_id,))
            if existing:
                # 更新现有记录
                return self.update({'info': value}, "id = ?", (meta_id,))
            else:
                # 插入新记录（需要指定 id）
                # 注意：由于 id 是 auto_increment，我们需要手动插入指定 id
                with self.db.get_sync_cursor() as cursor:
                    # 使用 INSERT ... ON CONFLICT 语法
                    cursor.execute(
                        f"INSERT INTO {self.table_name} (id, info) VALUES (?, ?) ON CONFLICT (id) DO UPDATE SET info = ?",
                        (meta_id, value, value)
                    )
                    return 1
        except Exception as e:
            logger.error(f"保存元信息失败: {e}")
            return 0
    
    def delete_by_key(self, key: str) -> int:
        """删除指定key的元信息"""
        meta_id = self.META_IDS.get(key)
        if not meta_id:
            logger.warning(f"未知的元信息键: {key}")
            return 0
        
        try:
            return self.delete("id = ?", (meta_id,))
        except Exception as e:
            logger.error(f"删除元信息失败: {e}")
            return 0

