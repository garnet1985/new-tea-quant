"""
sys_meta_info 表 Model

系统元信息。
"""
from typing import Optional, Dict, Any, List
from core.infra.db import DbBaseModel
from core.tables.system.meta_info.schema import schema as _schema


class SysMetaInfoModel(DbBaseModel):
    """系统元信息表 Model（表名 sys_meta_info）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_schema(self) -> dict:
        return _schema

    def load_by_id(self, id: int) -> Optional[Dict[str, Any]]:
        return self.load_one("id = %s", (id,))

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.replace(records, unique_keys=["id"])
