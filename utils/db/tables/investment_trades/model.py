"""
Investment Trades 模型
投资交易表，记录一笔投资的基本信息
"""
from utils.db.db_model import BaseTableModel
from typing import List, Dict, Any, Optional
from loguru import logger


class InvestmentTradesModel(BaseTableModel):
    """投资交易表模型"""
    
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        # 标记为基础表
        self.is_base_table = True
    
    def load_by_stock(self, stock_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        根据股票ID查询交易
        
        Args:
            stock_id: 股票代码
            status: 状态过滤 (open/closed)，None表示不过滤
            
        Returns:
            List[Dict]: 交易列表
        """
        if status:
            return self.load("stock_id = %s AND status = %s", (stock_id, status), order_by="created_at DESC")
        return self.load("stock_id = %s", (stock_id,), order_by="created_at DESC")
    
    def load_all_open(self) -> List[Dict[str, Any]]:
        """获取所有持仓中的交易"""
        return self.load("status = 'open'", order_by="created_at DESC")
    
    def load_all_closed(self) -> List[Dict[str, Any]]:
        """获取所有已平仓的交易"""
        return self.load("status = 'closed'", order_by="created_at DESC")

