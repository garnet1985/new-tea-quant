"""
板块定义表 Model（表名 sys_boards）
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel

from core.tables.stock.boards.schema import schema as _schema


class BoardsModel(DbBaseModel):
    """板块定义表 Model（表名 sys_boards）"""

    def __init__(self, db=None):
        super().__init__(_schema["name"], db)

    def load_by_id(self, board_id: int) -> Optional[Dict[str, Any]]:
        """按 id 查询"""
        return self.load_one("id = %s", (board_id,))

    def load_by_value(self, value: str) -> Optional[Dict[str, Any]]:
        """按板块名查询"""
        return self.load_one("value = %s", (value,))

    def load_alive(self) -> List[Dict[str, Any]]:
        """查询所有有效板块"""
        return self.load("is_alive = 1", order_by="id ASC")
