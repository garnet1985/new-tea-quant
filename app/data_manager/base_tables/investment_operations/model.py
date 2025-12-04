"""
投资操作记录 Model
"""
from typing import List, Dict, Any, Optional
from utils.db.db_model import BaseTableModel


class InvestmentOperationsModel(BaseTableModel):
    """投资操作记录 Model"""
    
    def __init__(self, db=None):
        super().__init__('investment_operations', db)
    
    def load_by_trade(self, trade_id: int) -> List[Dict[str, Any]]:
        """查询指定交易的所有操作记录"""
        return self.load("trade_id = %s", (trade_id,), order_by="operation_date ASC")
    
    def load_by_stock(self, stock_id: str) -> List[Dict[str, Any]]:
        """查询指定股票的所有操作记录"""
        return self.load("stock_id = %s", (stock_id,), order_by="operation_date DESC")
    
    def load_by_date_range(
        self, 
        start_date: str, 
        end_date: str
    ) -> List[Dict[str, Any]]:
        """查询指定日期范围的操作记录"""
        return self.load(
            "operation_date BETWEEN %s AND %s",
            (start_date, end_date),
            order_by="operation_date ASC"
        )
    
    def save_operations(self, operations: List[Dict[str, Any]]) -> int:
        """批量保存操作记录"""
        return self.save_many(operations)

