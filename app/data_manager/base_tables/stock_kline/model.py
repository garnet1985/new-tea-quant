"""
股票K线数据 Model
"""
from typing import List, Dict, Any, Optional
from utils.db import DbBaseModel


class StockKlineModel(DbBaseModel):
    """股票K线数据 Model"""
    
    def __init__(self, db=None):
        super().__init__('stock_kline', db)
    
    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        """查询指定股票的所有K线"""
        return self.load("id = %s", (stock_id,), order_by="date ASC")
    
    def load_by_date_range(
        self, 
        stock_id: str, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """查询指定日期范围的K线"""
        return self.load(
            "id = %s AND date BETWEEN %s AND %s",
            (stock_id, start_date, end_date),
            order_by="date ASC"
        )
    
    def load_latest(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """查询股票的最新K线"""
        return self.load_one("id = %s", (stock_id,), order_by="date DESC")
    
    def load_by_date(self, date: str) -> List[Dict[str, Any]]:
        """查询指定日期的所有股票K线"""
        return self.load("date = %s", (date,))
    
    def save_klines(self, klines: List[Dict[str, Any]]) -> int:
        """批量保存K线（自动去重）"""
        return self.replace(klines, unique_keys=['id', 'date'])

