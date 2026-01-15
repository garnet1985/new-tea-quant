"""
数据库适配器模块

提供统一的数据库接口，支持多种数据库后端（PostgreSQL、MySQL、SQLite）
"""
from .base_adapter import BaseDatabaseAdapter
from .factory import DatabaseAdapterFactory

__all__ = [
    'BaseDatabaseAdapter',
    'DatabaseAdapterFactory',
]
