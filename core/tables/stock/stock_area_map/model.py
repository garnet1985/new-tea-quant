"""
股票-地域映射表 Model（表名 sys_stock_area_map）
"""
from typing import List, Dict, Any
from core.infra.db.contracts import DbBaseModel

from core.tables.stock.stock_area_map.schema import schema as _schema


class StockAreaMapModel(DbBaseModel):
    """股票-地域映射表 Model（表名 sys_stock_area_map）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def replace_mapping(self, rows: List[Dict[str, Any]]) -> int:
        return self.upsert_many(rows, unique_keys=["stock_id", "area_id"])
