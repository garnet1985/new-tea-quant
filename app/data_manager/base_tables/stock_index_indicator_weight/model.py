"""
指数权重 Model
"""
from typing import List, Dict, Any, Optional
from utils.db import DbBaseModel


class StockIndexIndicatorWeightModel(DbBaseModel):
    """指数权重 Model"""
    
    def __init__(self, db=None):
        super().__init__('stock_index_indicator_weight', db)
    
    def load_by_index(self, index_code: str) -> List[Dict[str, Any]]:
        """查询指定指数的所有成分股权重"""
        return self.load("index_code = %s", (index_code,), order_by="trade_date DESC")
    
    def load_by_date(
        self, 
        index_code: str, 
        date: str
    ) -> List[Dict[str, Any]]:
        """查询指定指数指定日期的成分股权重"""
        return self.load(
            "index_code = %s AND trade_date = %s",
            (index_code, date)
        )
    
    def load_by_stock(
        self, 
        index_code: str, 
        stock_code: str
    ) -> List[Dict[str, Any]]:
        """查询指定股票在指数中的权重历史"""
        return self.load(
            "index_code = %s AND con_code = %s",
            (index_code, stock_code),
            order_by="trade_date DESC"
        )
    
    def save_weights(self, weights: List[Dict[str, Any]]) -> int:
        """批量保存权重数据（自动去重）"""
        return self.replace(weights, unique_keys=['index_code', 'con_code', 'trade_date'])

