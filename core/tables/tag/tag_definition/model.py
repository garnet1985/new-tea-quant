"""
sys_tag_definition 表 Model

标签定义。
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel
from core.tables.tag.tag_definition.schema import schema as _schema


class SysTagDefinitionModel(DbBaseModel):
    """标签定义表 Model（表名 sys_tag_definition）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_schema(self) -> dict:
        return _schema

    def load_by_scenario(self, scenario_id: int) -> List[Dict[str, Any]]:
        return self.load("scenario_id = %s", (scenario_id,))

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.replace(records, unique_keys=["id"])
