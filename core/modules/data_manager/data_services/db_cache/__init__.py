"""
数据库缓存服务模块（DbCacheService）

职责：
- 封装数据库缓存相关的查询和数据操作
- 提供系统缓存的统一访问接口

涉及的表：
- system_cache: 系统缓存表
"""

from .db_cache_service import DbCacheService

__all__ = [
    'DbCacheService',
]
