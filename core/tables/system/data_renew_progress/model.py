"""sys_meta_data_renew_progress 的读写。"""
from typing import List, Dict, Any

from core.infra.db.contracts import DbBaseModel
from core.tables.system.data_renew_progress.schema import schema as _schema


class SysDataRenewProgressModel(DbBaseModel):
    """按 (source, entity_id, term) 记下已经更新到的数据日期。"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        """按主键覆盖写入。调用方要保证日期只往更晚改。"""
        return self.upsert_many(
            records,
            unique_keys=["source", "entity_id", "term"],
        )
