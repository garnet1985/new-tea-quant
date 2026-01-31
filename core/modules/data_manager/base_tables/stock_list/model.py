"""
股票列表 Model

DEPRECATED: 本表定义已废弃。实际使用的表为 core/tables/stock/stock_list（sys_stock_list），
由 DataManager 从 core/tables 发现并注册。请勿再依赖本 base_tables 下的 schema/model。
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel


class StockListModel(DbBaseModel):
    """股票列表 Model（已废弃，请使用 core/tables/stock/stock_list）"""

    def __init__(self, db=None):
        super().__init__('stock_list', db)
    
    def load_by_id(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """根据股票代码查询"""
        return self.load_one("id = %s", (stock_id,))
    
    def load_by_name(self, name: str) -> List[Dict[str, Any]]:
        """根据股票名称模糊查询"""
        return self.load("name LIKE %s", (f"%{name}%",))
    
    def load_active_stocks(self) -> List[Dict[str, Any]]:
        """查询所有活跃股票"""
        return self.load("1=1", order_by="id ASC")
    
    def save_stocks(self, stocks: List[Dict[str, Any]]) -> int:
        """批量保存股票（自动去重）"""
        return self.replace(stocks, unique_keys=['id'])

