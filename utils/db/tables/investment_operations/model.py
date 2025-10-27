"""
Investment Operations 模型
投资操作表，记录每次买入、卖出、补仓等操作
"""
from utils.db.db_model import BaseTableModel
from typing import List, Dict, Any, Optional
from loguru import logger


class InvestmentOperationsModel(BaseTableModel):
    """投资操作表模型"""
    
    def __init__(self, table_name: str, connected_db):
        super().__init__(table_name, connected_db)
        # 标记为基础表
        self.is_base_table = True
    
    def load_by_trade(self, trade_id: int, order_by: str = "date ASC") -> List[Dict[str, Any]]:
        """
        根据交易ID查询所有操作记录
        
        Args:
            trade_id: 交易ID
            order_by: 排序方式
            
        Returns:
            List[Dict]: 操作记录列表
        """
        return self.load("trade_id = %s", (trade_id,), order_by=order_by)
    
    def load_by_type(self, trade_id: int, op_type: str) -> List[Dict[str, Any]]:
        """
        根据操作类型查询
        
        Args:
            trade_id: 交易ID
            op_type: 操作类型 (buy/sell/add)
            
        Returns:
            List[Dict]: 操作记录列表
        """
        return self.load("trade_id = %s AND type = %s", (trade_id, op_type), order_by="date ASC")
    
    def get_total_buy_amount(self, trade_id: int) -> int:
        """
        获取总买入数量
        
        Args:
            trade_id: 交易ID
            
        Returns:
            int: 总买入数量
        """
        operations = self.load_by_type(trade_id, 'buy')
        total = sum(op['amount'] for op in operations)
        operations_add = self.load_by_type(trade_id, 'add')
        total += sum(op['amount'] for op in operations_add)
        return total
    
    def get_total_sell_amount(self, trade_id: int) -> int:
        """
        获取总卖出数量
        
        Args:
            trade_id: 交易ID
            
        Returns:
            int: 总卖出数量
        """
        operations = self.load_by_type(trade_id, 'sell')
        return sum(op['amount'] for op in operations)
    
    def get_current_holding(self, trade_id: int) -> Dict[str, Any]:
        """
        计算当前持仓信息
        
        Args:
            trade_id: 交易ID
            
        Returns:
            Dict: {
                'amount': 当前持仓数量,
                'avg_cost': 平均成本,
                'total_cost': 总成本,
                'first_buy_date': 首次买入日期,
                'first_buy_price': 首次买入价格
            }
        """
        operations = self.load_by_trade(trade_id, order_by="date ASC")
        
        total_buy = 0
        total_cost = 0.0
        first_buy = None
        
        for op in operations:
            if op['type'] in ['buy', 'add']:
                if first_buy is None:
                    first_buy = {
                        'date': op['date'],
                        'price': float(op['price']),
                        'amount': op['amount']
                    }
                total_buy += op['amount']
                total_cost += float(op['price']) * op['amount']
            elif op['type'] == 'sell':
                total_buy -= op['amount']
        
        avg_cost = total_cost / total_buy if total_buy > 0 else 0
        
        return {
            'amount': total_buy,
            'avg_cost': round(avg_cost, 2),
            'total_cost': round(total_cost, 2),
            'first_buy_date': first_buy['date'] if first_buy else None,
            'first_buy_price': round(first_buy['price'], 2) if first_buy else None
        }

