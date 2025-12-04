"""
复权因子 Model
"""
from typing import List, Dict, Any, Optional
from utils.db.db_model import BaseTableModel


class AdjFactorModel(BaseTableModel):
    """复权因子 Model"""
    
    def __init__(self, db):
        super().__init__('adj_factor', db)
    
    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        """查询指定股票的所有复权因子"""
        return self.load("id = %s", (stock_id,), order_by="trade_date ASC")
    
    def load_by_date_range(
        self, 
        stock_id: str, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """查询指定日期范围的复权因子"""
        return self.load(
            "id = %s AND trade_date BETWEEN %s AND %s",
            (stock_id, start_date, end_date),
            order_by="trade_date ASC"
        )
    
    def load_by_date(self, stock_id: str, date: str) -> Optional[Dict[str, Any]]:
        """查询指定日期的复权因子"""
        return self.load_one(
            "id = %s AND trade_date <= %s",
            (stock_id, date),
            order_by="trade_date DESC"
        )
    
    def save_factors(self, factors: List[Dict[str, Any]]) -> int:
        """批量保存复权因子（自动去重）"""
        return self.replace(factors, unique_keys=['id', 'trade_date'])

