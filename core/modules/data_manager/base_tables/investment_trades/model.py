"""
投资交易记录 Model
"""
from typing import List, Dict, Any, Optional
from core.infra.db import DbBaseModel


class InvestmentTradesModel(DbBaseModel):
    """投资交易记录 Model"""
    
    def __init__(self, db=None):
        super().__init__('investment_trades', db)
    
    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        """查询指定股票的所有交易记录"""
        return self.load("stock_id = %s", (stock_id,), order_by="created_at DESC")
    
    def load_by_strategy(self, strategy: str) -> List[Dict[str, Any]]:
        """查询指定策略的所有交易记录"""
        return self.load("strategy = %s", (strategy,), order_by="created_at DESC")
    
    def load_active_trades(self) -> List[Dict[str, Any]]:
        """查询所有未平仓的交易"""
        return self.load("status = %s", ('active',), order_by="created_at DESC")
    
    def load_by_id(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """根据交易ID查询"""
        return self.load_one("id = %s", (trade_id,))
    
    def save_trades(self, trades: List[Dict[str, Any]]) -> int:
        """批量保存交易记录"""
        return self.save_many(trades)

