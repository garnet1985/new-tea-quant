"""
板块维度表 Model（sys_stock_boards）
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel

from core.tables.stock.stock_boards.schema import schema as _schema


class DataBoardsModel(DbBaseModel):
    """板块维度表 Model（表名 sys_stock_boards）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_id(self, board_id: int) -> Optional[Dict[str, Any]]:
        """按 id 查询"""
        return self.load_one("id = %s", (board_id,))

    def load_by_value(self, value: str) -> Optional[Dict[str, Any]]:
        """按板块名查询"""
        return self.load_one("value = %s", (value,))

    def load_active(self) -> List[Dict[str, Any]]:
        """查询所有有效板块（is_alive = 1，旧表字段命名保留）"""
        return self.load("is_alive = 1", order_by="id ASC")
