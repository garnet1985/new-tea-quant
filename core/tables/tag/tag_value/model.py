"""
sys_tag_value 表 Model

标签值。
"""
from typing import List, Dict, Any
from core.infra.db import DbBaseModel
from core.tables.tag.tag_value.schema import schema as _schema


class SysTagValueModel(DbBaseModel):
    """标签值表 Model（表名 sys_tag_value）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.replace(
            records,
            unique_keys=["entity_id", "tag_definition_id", "as_of_date"],
        )
