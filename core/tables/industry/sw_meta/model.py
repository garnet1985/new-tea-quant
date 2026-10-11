"""申万行业分类 Model（表名 sys_data_sw_industry）。"""
from typing import Any, Dict, List

from core.infra.db.contracts import DbBaseModel

from core.tables.industry.sw_meta.schema import schema as _schema


class SwIndustryModel(DbBaseModel):
    """申万行业分类 Model（表名 sys_data_sw_industry）。"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.upsert_many(records, unique_keys=["id"])
