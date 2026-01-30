"""
data_shibor 表 Model

上海银行间同业拆放利率。
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel
from core.tables.data_shibor.schema import schema as _schema


class DataShiborModel(DbBaseModel):
    """Shibor 表 Model（表名 data_shibor）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_schema(self) -> dict:
        return _schema

    def load_by_date(self, date: str) -> Optional[Dict[str, Any]]:
        return self.load_one("date = %s", (date,))

    def load_by_date_range(
        self, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        return self.load(
            "date BETWEEN %s AND %s",
            (start_date, end_date),
            order_by="date ASC",
        )

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        return self.replace(records, unique_keys=["date"])
