"""
sys_cache 表 Model

系统缓存：支持 text / json 两种存储形式；写入时维护 created_at、last_updated。
"""
from datetime import datetime
from typing import Optional, Dict, Any
import logging

from core.infra.db import DbBaseModel

from core.tables.system.system_cache.schema import schema as _schema


logger = logging.getLogger(__name__)


class CacheSystemModel(DbBaseModel):
    """系统缓存表 Model（表名 sys_cache）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def is_exists(self, key: str) -> bool:
        v = self.load_one('"key" = %s', (key,))
        if v:
            return True
        return False

    def load_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """根据 key 查询，返回整行（含 text/json、created_at、last_updated）。"""
        return self.load_one('"key" = %s', (key,))

    def save_by_key(self, key: str, text: str = None, json: Optional[Dict[str, Any]] = None) -> int:
        if not key:
            logger.warning(f"设置缓存值时，key 不能为空")
            return 0
        params = {
            "key": key,
        }
        if json or text:
            params["text"] = text
            params["json"] = json
        else:
            logger.warning(f"设置缓存值时，text 和 json 不能同时为空")
            return 0
        
        now = datetime.now()
        params["last_updated"] = now

        if not self.is_exists(key):
            params["created_at"] = now

        # 使用 upsert_one 同步落库，避免走写入队列导致进程退出前未 flush
        return self.upsert_one(params, unique_keys=["key"])

    def load_meta(self, key: str) -> Optional[Dict[str, Any]]:
        """根据 key 查询，返回 created_at、last_updated。"""
        v = self.load_one('"key" = %s', (key,))
        if v:
            return {
                "created_at": v.get("created_at"),
                "last_updated": v.get("last_updated"),
            }
        return None

    def delete_by_key(self, key: str) -> int:
        """按 key 删除一行。"""
        return self.delete_one('"key" = %s', (key,))
