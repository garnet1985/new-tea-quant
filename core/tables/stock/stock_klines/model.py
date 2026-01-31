"""
stock_klines 表 Model
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel

from core.tables.stock.stock_klines.schema import schema as _schema


class DataStockKlinesModel(DbBaseModel):
    """股票 K 线表 Model（表名 sys_stock_klines，含 daily/weekly/monthly）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_date(self, date: str) -> List[Dict[str, Any]]:
        """查询指定日期的所有 K 线（所有股票、所有周期）"""
        return self.load("date = %s", (date,), order_by="id ASC, term ASC")

    def load_by_stock(self, stock_id: str, term: Optional[str] = None) -> List[Dict[str, Any]]:
        """查询指定股票 K 线；term 为空则查全部周期"""
        if term:
            return self.load("id = %s AND term = %s", (stock_id, term), order_by="date ASC")
        return self.load("id = %s", (stock_id,), order_by="term ASC, date ASC")

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
        """批量保存 K 线（按 id+term+date 去重）"""
        return self.replace(klines, unique_keys=["id", "term", "date"])
