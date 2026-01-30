"""
cache_system 表 Model

系统缓存。
"""
from typing import Optional, Dict, Any
from core.infra.db import DbBaseModel
from core.tables.cache_system.schema import schema as _schema


class CacheSystemModel(DbBaseModel):
    """系统缓存表 Model（表名 cache_system）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_schema(self) -> dict:
        return _schema

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self.load_one("key = %s", (key,))

    def set(self, key: str, value: str) -> int:
        return self.replace([{"key": key, "value": value}], unique_keys=["key"])
