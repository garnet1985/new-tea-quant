"""
市场定义表 Model（表名 sys_markets）
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel

from core.tables.stock.markets.schema import schema as _schema


class MarketsModel(DbBaseModel):
    """市场定义表 Model（表名 sys_markets）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_id(self, market_id: int) -> Optional[Dict[str, Any]]:
        """按 id 查询"""
        return self.load_one("id = %s", (market_id,))

    def load_by_value(self, value: str) -> Optional[Dict[str, Any]]:
        """按市场名查询"""
        return self.load_one("value = %s", (value,))

    def load_active(self) -> List[Dict[str, Any]]:
        """查询所有有效市场（is_active = 1）"""
        return self.load("is_active = 1", order_by="id ASC")
