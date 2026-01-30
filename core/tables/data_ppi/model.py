"""
data_ppi 表 Model

生产者价格指数（原 price_indexes 拆分）。
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel

from core.tables.data_ppi.schema import schema as _schema


class DataPpiModel(DbBaseModel):
    """PPI 表 Model（表名 data_ppi）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_schema(self) -> dict:
        """从本表 schema.py 加载"""
        return _schema

    def load_by_month(self, month: str) -> Optional[Dict[str, Any]]:
        """查询指定月份"""
        return self.load_one("date = %s", (month,))

    def load_by_date_range(
        self, start_month: str, end_month: str
    ) -> List[Dict[str, Any]]:
        """查询月份范围"""
        return self.load(
            "date BETWEEN %s AND %s",
            (start_month, end_month),
            order_by="date ASC",
        )

    def load_latest(self) -> Optional[Dict[str, Any]]:
        """查询最新一条"""
        return self.load_one("1=1", order_by="date DESC")

    def save_records(self, records: List[Dict[str, Any]]) -> int:
        """批量保存（按 date 去重）"""
        return self.replace(records, unique_keys=["date"])
