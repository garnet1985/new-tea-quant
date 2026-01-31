"""
股票-市场映射表 Model（表名 sys_stock_market_map）
"""
from typing import List, Dict, Any
from core.infra.db import DbBaseModel

from core.tables.stock.stock_market_map.schema import schema as _schema


class StockMarketMapModel(DbBaseModel):
    """股票-市场映射表 Model（表名 sys_stock_market_map）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def replace_mapping(self, rows: List[Dict[str, Any]]) -> int:
        """批量替换映射（按 stock_id, market_id 去重）"""
        return self.replace(rows, unique_keys=["stock_id", "market_id"], use_batch=True)
