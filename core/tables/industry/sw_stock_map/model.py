"""股票申万行业映射 Model（表名 sys_map_sw_stock_industry）。"""
from typing import Any, Dict, List

from core.infra.db.contracts import DbBaseModel

from core.tables.industry.sw_stock_map.schema import schema as _schema


class SwStockIndustryModel(DbBaseModel):
    """股票申万行业映射 Model（表名 sys_map_sw_stock_industry）。"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.upsert_many(records, unique_keys=["stock_id"])
