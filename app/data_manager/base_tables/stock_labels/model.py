"""
股票标签 Model
"""
from typing import List, Dict, Any, Optional
from utils.db import DbBaseModel


class StockLabelsModel(DbBaseModel):
    """股票标签 Model"""
    
    def __init__(self, db=None):
        super().__init__('stock_labels', db)
    
    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        """查询指定股票的所有标签"""
        return self.load("id = %s", (stock_id,), order_by="date DESC")
    
    def load_by_date(
        self, 
        stock_id: str, 
        date: str
    ) -> Optional[Dict[str, Any]]:
        """查询指定股票指定日期的标签"""
        return self.load_one("id = %s AND date = %s", (stock_id, date))
    
    def load_by_date_range(
        self, 
        stock_id: str, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """查询指定日期范围的标签"""
        return self.load(
            "id = %s AND date BETWEEN %s AND %s",
            (stock_id, start_date, end_date),
            order_by="date ASC"
        )
    
    def save_labels(self, labels: List[Dict[str, Any]]) -> int:
        """批量保存标签（自动去重）"""
        return self.replace(labels, unique_keys=['id', 'date'])

