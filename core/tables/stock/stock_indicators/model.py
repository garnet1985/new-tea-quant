"""
data_stock_indicators 表 Model

股票日度基本面指标（原 daily_basic），与 K 线表分离。
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel

from core.tables.stock.stock_indicators.schema import schema as _schema


class DataStockIndicatorsModel(DbBaseModel):
    """股票指标表 Model（表名 data_stock_indicators）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        """查询指定股票指标"""
        return self.load("id = %s", (stock_id,), order_by="date ASC")

    def load_by_date_range(
        self, stock_id: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """查询指定日期范围指标"""
        return self.load(
            "id = %s AND date BETWEEN %s AND %s",
            (stock_id, start_date, end_date),
            order_by="date ASC",
        )

    def load_latest(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """查询股票最新指标"""
        return self.load_one("id = %s", (stock_id,), order_by="date DESC")

    def save_indicators(self, records: List[Dict[str, Any]]) -> int:
        """批量保存指标（自动去重）"""
        return self.upsert_many(records, unique_keys=["id", "date"])
