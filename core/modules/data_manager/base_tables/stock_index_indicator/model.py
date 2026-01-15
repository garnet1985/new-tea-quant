"""
指数指标 Model
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel


class StockIndexIndicatorModel(DbBaseModel):
    """指数指标 Model"""
    
    def __init__(self, db=None):
        super().__init__('stock_index_indicator', db)
    
    def load_by_index(self, index_code: str) -> List[Dict[str, Any]]:
        """查询指定指数的所有指标"""
        return self.load("id = %s", (index_code,), order_by="trade_date DESC")
    
    def load_by_date(
        self, 
        index_code: str, 
        date: str
    ) -> Optional[Dict[str, Any]]:
        """查询指定指数指定日期的指标"""
        return self.load_one("id = %s AND trade_date = %s", (index_code, date))
    
    def load_latest(self, index_code: str) -> Optional[Dict[str, Any]]:
        """查询指数的最新指标"""
        return self.load_one("id = %s", (index_code,), order_by="trade_date DESC")
    
    def save_indicators(self, indicators: List[Dict[str, Any]]) -> int:
        """批量保存指标（自动去重）"""
        return self.replace(indicators, unique_keys=['id', 'trade_date'])

