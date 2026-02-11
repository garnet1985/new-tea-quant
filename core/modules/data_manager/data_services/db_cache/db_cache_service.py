"""
数据库缓存服务（DbCacheService）

职责：
- 封装数据库缓存相关的查询和数据操作
- 提供系统缓存的统一访问接口

涉及的表：
- system_cache: 系统缓存表
"""
import datetime
from typing import List, Dict, Any, Optional
import logging

from .. import BaseDataService


logger = logging.getLogger(__name__)


class DbCacheService(BaseDataService):
    """数据库缓存服务"""
    
    def __init__(self, data_manager: Any):
        """
        初始化数据库缓存服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
        
        # 获取相关 Model - 私有属性，不对外暴露
        self._cache_model = data_manager.get_table("sys_cache")
        
        # 获取 DatabaseManager 用于复杂 SQL 查询
        from core.infra.db import DatabaseManager
        self.db = DatabaseManager.get_default(auto_init=True)
    
    # ==================== 缓存操作方法 ====================

    def is_exists(self, key: str) -> bool:
        """
        判断缓存是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            True 表示缓存存在，False 表示缓存不存在
        """
        return self._cache_model.is_exists(key)

    def load_meta(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存元信息
        
        Args:
            key: 缓存键
            
        Returns:
            created_at、last_updated
        """
        return self._cache_model.load_meta(key)

    def load_last_updated(self, key: str) -> Optional[str]:
        """
        获取缓存最后更新时间
        
        Args:
            key: 缓存键
            
        Returns:
            last_updated
        """
        meta = self.load_meta(key)
        if meta:
            return meta.get("last_updated")
        return None

    def load_created_at(self, key: str) -> Optional[str]:
        """
        获取缓存创建时间
        
        Args:
            key: 缓存键
            
        Returns:
            created_at
        """
        meta = self.load_meta(key)
        if meta:
            return meta.get("created_at")
        return None

    def load_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            True 表示缓存存在，False 表示缓存不存在
        """
        value = self._cache_model.load_by_key(key)
        if value:
            return value.get("json")
        return None

    def load_text(self, key: str) -> Optional[str]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            True 表示缓存存在，False 表示缓存不存在
        """
        value = self._cache_model.load_by_key(key)
        if value:
            return value.get("text")
        return None

    def load(self, key: str, field: str = "json") -> Optional[Dict[str, Any]]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            field: 字段名
        Returns:
            True 表示缓存存在，False 表示缓存不存在
        """

        if field == "json":
            return self.load_json(key)
        elif field == "text":
            return self.load_text(key)
        else:
            logger.warning(f"{self._cache_model.table_name} 不支持的字段名: {field}")
            return None

    def save(self, key: str, text: str = None, json: Optional[Dict[str, Any]] = None) -> int:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            text: 缓存值
            json: 缓存值
            
        Returns:
            影响的行数
        """

        return self._cache_model.save_by_key(key, text=text, json=json)

    
    def delete(self, key: str) -> int:
        """
        删除缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            影响的行数
        """
        return self._cache_model.delete_by_key(key)