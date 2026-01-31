"""
data_gdp 表 Model

国内生产总值。
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel
from core.tables.macro.gdp.schema import schema as _schema


class DataGdpModel(DbBaseModel):
    """GDP 表 Model（表名 data_gdp）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_schema(self) -> dict:
        return _schema

    def load_by_quarter(self, quarter: str) -> Optional[Dict[str, Any]]:
        return self.load_one("quarter = %s", (quarter,))

    def load_by_date_range(
        self, start_quarter: str, end_quarter: str
    ) -> List[Dict[str, Any]]:
        return self.load(
            "quarter BETWEEN %s AND %s",
            (start_quarter, end_quarter),
            order_by="quarter ASC",
        )

    def load_latest(self) -> Optional[Dict[str, Any]]:
        return self.load_one("1=1", order_by="quarter DESC")

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.replace(records, unique_keys=["quarter"])
