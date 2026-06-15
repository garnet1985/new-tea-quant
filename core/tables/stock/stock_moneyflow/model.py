"""
个股资金流向表 Model（sys_stock_moneyflow）
"""
from typing import List, Dict, Any, Optional

from core.infra.db import DbBaseModel

from core.tables.stock.stock_moneyflow.schema import schema as _schema


class DataStockMoneyflowModel(DbBaseModel):
    """个股资金流向 Model"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        return self.load("id = %s", (stock_id,), order_by="date ASC")

    def load_by_date_range(
        self, stock_id: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        return self.load(
            "id = %s AND date BETWEEN %s AND %s",
            (stock_id, start_date, end_date),
            order_by="date ASC",
        )

    def load_latest(self, stock_id: str) -> Optional[Dict[str, Any]]:
        return self.load_one("id = %s", (stock_id,), order_by="date DESC")
