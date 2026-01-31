"""
sys_cache 表 Model

系统缓存：value 为 text；写入时维护 created_at、last_updated。
"""
from datetime import datetime
from typing import Optional, Dict, Any

from core.infra.db import DbBaseModel

from core.tables.system.system_cache.schema import schema as _schema


class CacheSystemModel(DbBaseModel):
    """系统缓存表 Model（表名 sys_cache）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """根据 key 查询，返回整行（含 value、created_at、last_updated）。"""
        return self.load_one('"key" = %s', (key,))

    def save_cache(self, key: str, value: str) -> int:
        """保存或更新：新插入时写 created_at、last_updated；更新时只写 value、last_updated。"""
        now = datetime.now()
        row = self.load_by_key(key)
        if row and row.get("created_at") is not None:
            return self.replace(
                [{"key": key, "value": value, "created_at": row["created_at"], "last_updated": now}],
                unique_keys=["key"],
            )
        return self.replace(
            [{"key": key, "value": value, "created_at": now, "last_updated": now}],
            unique_keys=["key"],
        )

    def delete_by_key(self, key: str) -> int:
        """按 key 删除一行。"""
        return self.delete_one('"key" = %s', (key,))
