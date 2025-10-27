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
        
        计算逻辑：
        - 买入/补仓：增加持仓数量和成本
        - 卖出：减少持仓数量和成本（按当前平均成本扣除）
        - 首次买入：通过is_first字段识别
        
        Args:
            trade_id: 交易ID
            
        Returns:
            Dict: {
                'amount': 当前持仓数量,
                'avg_cost': 平均成本,
                'total_cost': 总成本,
                'first_buy_date': 首次买入日期,
                'first_buy_price': 首次买入价格,
                'realized_profit': 已实现盈利（元）,
                'realized_profit_rate': 已实现盈利率（%）
            }
        """
        operations = self.load_by_trade(trade_id, order_by="date ASC")
        
        total_amount = 0
        total_cost = 0.0
        first_buy = None
        realized_profit = 0.0  # 已实现盈利
        
        # 从数据库中获取标记为is_first的记录
        first_buy_op = self.load_one("trade_id = %s AND is_first = 1", (trade_id,))
        if first_buy_op:
            first_buy = {
                'date': first_buy_op['date'],
                'price': float(first_buy_op['price']),
                'amount': first_buy_op['amount']
            }
        
        for op in operations:
            if op['type'] in ['buy', 'add']:
                # 买入：增加数量和成本
                total_amount += op['amount']
                total_cost += float(op['price']) * op['amount']
            elif op['type'] == 'sell':
                # 卖出：减少数量和成本（按当前平均成本扣除）
                sell_amount = op['amount']
                current_avg_cost = total_cost / total_amount if total_amount > 0 else 0
                sell_price = float(op['price'])
                
                # 计算本次卖出的盈利
                cost_of_sell = current_avg_cost * sell_amount
                profit_of_sell = (sell_price - current_avg_cost) * sell_amount
                realized_profit += profit_of_sell
                
                total_amount -= sell_amount
                total_cost -= cost_of_sell
        
        avg_cost = total_cost / total_amount if total_amount > 0 else 0
        
        # 计算已实现盈利率（相对于总投入）
        total_invested = sum(float(op['price']) * op['amount'] for op in operations if op['type'] in ['buy', 'add'])
        realized_profit_rate = (realized_profit / total_invested * 100) if total_invested > 0 else 0
        
        return {
            'amount': total_amount,
            'avg_cost': round(avg_cost, 2),
            'total_cost': round(total_cost, 2),
            'first_buy_date': first_buy['date'] if first_buy else None,
            'first_buy_price': round(first_buy['price'], 2) if first_buy else None,
            'realized_profit': round(realized_profit, 2),
            'realized_profit_rate': round(realized_profit_rate, 4)
        }

