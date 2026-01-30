"""
data_stock_kline_daily 表 Model
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel

from core.tables.data_stock_kline_daily.schema import schema as _schema


class DataStockKlineDailyModel(DbBaseModel):
    """日 K 线表 Model（表名 data_stock_kline_daily）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_schema(self) -> dict:
        """从本表 schema.py 加载"""
        return _schema

    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        """查询指定股票日 K 线"""
        return self.load("id = %s", (stock_id,), order_by="date ASC")

    def load_by_date_range(
        self, stock_id: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """查询指定日期范围日 K 线"""
        return self.load(
            "id = %s AND date BETWEEN %s AND %s",
            (stock_id, start_date, end_date),
            order_by="date ASC",
        )

    def load_latest(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """查询股票最新日 K 线"""
        return self.load_one("id = %s", (stock_id,), order_by="date DESC")

    def save_klines(self, klines: List[Dict[str, Any]]) -> int:
        """批量保存日 K 线（自动去重）"""
        return self.replace(klines, unique_keys=["id", "date"])
