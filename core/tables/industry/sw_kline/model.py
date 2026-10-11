"""申万一级行业日线 Model（表名 sys_data_sw_industry_kline）。"""
from typing import Any, Dict, List

from core.infra.db.contracts import DbBaseModel

from core.tables.industry.sw_kline.schema import schema as _schema


class SwIndustryKlineModel(DbBaseModel):
    """申万一级行业日线 Model（表名 sys_data_sw_industry_kline）。"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.upsert_many(records, unique_keys=["id", "date"])
