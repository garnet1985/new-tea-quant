"""
数据库缓存服务（DbCacheService）

职责：
- 封装数据库缓存相关的查询和数据操作
- 提供系统缓存的统一访问接口

涉及的表：
- system_cache: 系统缓存表
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from .. import BaseDataService


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
        self._system_cache = data_manager.get_table("sys_cache")
        
        # 获取 DatabaseManager 用于复杂 SQL 查询
        from core.infra.db import DatabaseManager
        self.db = DatabaseManager.get_default(auto_init=True)
    
    # ==================== 缓存操作方法 ====================
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值字典（包含 'value' 字段），如果不存在返回 None
        """
        if not self._system_cache:
            return None
        
        return self._system_cache.load_by_key(key)
    
    def set(self, key: str, value: str) -> int:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            
        Returns:
            影响的行数
        """
        if not self._system_cache:
            return 0
        
        return self._system_cache.save_cache(key, value)
    
    def delete(self, key: str) -> int:
        """
        删除缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            影响的行数
        """
        if not self._system_cache:
            return 0
        
        return self._system_cache.delete_by_key(key)
    
    def get_value(self, key: str) -> Optional[str]:
        """
        获取缓存值（仅返回 value 字段）
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值字符串，如果不存在返回 None
        """
        cache_item = self.get(key)
        if cache_item:
            return cache_item.get('value')
        return None
