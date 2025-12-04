"""
股票列表 Model
"""
from typing import List, Dict, Any, Optional
from utils.db.db_model import BaseTableModel


class StockListModel(BaseTableModel):
    """股票列表 Model"""
    
    def __init__(self, db):
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

