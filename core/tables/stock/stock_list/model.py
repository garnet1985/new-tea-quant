"""
sys_stock_list 表 Model
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel

from core.tables.stock.stock_list.schema import schema as _schema


class DataStockListModel(DbBaseModel):
    """股票列表表 Model（表名 sys_stock_list）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_id(self, stock_id: str) -> Optional[Dict[str, Any]]:
        return self.load_one("id = %s", (stock_id,))

    def load_by_name(self, name: str) -> List[Dict[str, Any]]:
        return self.load("name LIKE %s", (f"%{name}%",))

    def load_all_stocks(self) -> List[Dict[str, Any]]:
        return self.load("1=1", order_by="id ASC")

    def save_stocks(self, stocks: List[Dict[str, Any]]) -> int:
        return self.upsert_many(stocks, unique_keys=["id"])
