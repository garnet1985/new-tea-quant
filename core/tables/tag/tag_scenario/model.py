"""
sys_tag_scenario 表 Model

业务场景。
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel
from core.tables.tag.tag_scenario.schema import schema as _schema


class SysTagScenarioModel(DbBaseModel):
    """业务场景表 Model（表名 sys_tag_scenario）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        return self.load_one("name = %s", (name,))

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.replace(records, unique_keys=["id"])
