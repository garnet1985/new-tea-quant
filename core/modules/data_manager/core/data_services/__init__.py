"""
Data Service 子模块

封装跨表 / 领域级数据访问；由 DataManager 创建与管理。

当前挂载：stock / macro / calendar / index / db_cache / backup_restore。
"""

from typing import Any


class BaseDataService:
    """DataService 基类。"""

    def __init__(self, data_manager: Any):
        self.data_manager = data_manager


from .data_service import DataService

__all__ = [
    "BaseDataService",
    "DataService",
]
