"""
投资数据服务

提供投资交易和操作记录的加载和保存功能，支持：
- 交易记录查询（investment_trades）
- 操作记录查询（investment_operations）
- 联合查询（交易 + 操作详情）
- 按状态查询（持仓中/已平仓）
"""

from typing import List, Dict, Any, Optional
from loguru import logger


class InvestmentDataService:
    """
    投资数据服务
    
    管理两张表：
    - investment_trades: 交易记录（一次完整交易，从开仓到平仓）
    - investment_operations: 操作记录（每次买入/卖出）
    """
    
    def __init__(self, data_manager):
        """
        初始化服务
        
        Args:
            data_manager: DataManager 实例
        """
        self.data_manager = data_manager
        self.trades_model = None
        self.operations_model = None
    
    def _get_trades_model(self):
        """获取交易表 Model（延迟初始化）"""
        if not self.trades_model:
            self.trades_model = self.data_manager.get_table("sys_investment_trades")
        return self.trades_model

    def _get_operations_model(self):
        """获取操作表 Model（延迟初始化）"""
        if not self.operations_model:
            self.operations_model = self.data_manager.get_table("sys_investment_operations")
        return self.operations_model
    
    # ========== 交易记录 (Trades) ==========
    
    def load_trade(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """
        加载指定交易记录
        
        Args:
            trade_id: 交易ID
        
        Returns:
            交易记录字典
        """
        model = self._get_trades_model()
        condition = "id = %s"
        params = (trade_id,)
        results = model.load(condition, params, limit=1)
        return results[0] if results else None
    
    def load_trades_by_stock(
        self, 
        stock_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载指定股票的交易记录
        
        Args:
            stock_id: 股票代码
            status: 状态筛选 ('open', 'closed')，None表示所有
        
        Returns:
            交易记录列表
        """
        model = self._get_trades_model()
        
        if status:
            condition = "stock_id = %s AND status = %s"
            params = (stock_id, status)
        else:
            condition = "stock_id = %s"
            params = (stock_id,)
        
        return model.load(condition, params, order_by="created_at DESC")
    
    def load_open_trades(self, strategy: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        加载所有持仓中的交易
        
        Args:
            strategy: 策略名称筛选，None表示所有策略
        
        Returns:
            持仓中的交易列表
        """
        model = self._get_trades_model()
        
        if strategy:
            condition = "status = 'open' AND strategy = %s"
            params = (strategy,)
        else:
            condition = "status = 'open'"
            params = ()
        
        return model.load(condition, params, order_by="created_at DESC")
    
    def load_closed_trades(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载已平仓的交易
        
        Args:
            start_date: 起始日期
            end_date: 结束日期
        
        Returns:
            已平仓的交易列表
        """
        model = self._get_trades_model()
        
        if start_date and end_date:
            condition = "status = 'closed' AND updated_at >= %s AND updated_at <= %s"
            params = (start_date, end_date)
        elif start_date:
            condition = "status = 'closed' AND updated_at >= %s"
            params = (start_date,)
        elif end_date:
            condition = "status = 'closed' AND updated_at <= %s"
            params = (end_date,)
        else:
            condition = "status = 'closed'"
            params = ()
        
        return model.load(condition, params, order_by="updated_at DESC")
    
    def save_trade(self, data: Dict[str, Any]) -> Optional[int]:
        """
        保存交易记录
        
        Args:
            data: 交易数据，必须包含 'stock_id'
        
        Returns:
            交易ID（新增或已存在的）
        """
        if 'stock_id' not in data:
            logger.error("交易数据必须包含 'stock_id' 字段")
            return None
        
        model = self._get_trades_model()
        
        # 如果有 id，使用 replace；否则 insert
        if 'id' in data and data['id']:
            affected = model.replace([data], ['id'])
            return data['id'] if affected >= 0 else None
        else:
            affected = model.insert([data])
            if affected > 0:
                # 获取最后插入的ID
                last_trade = model.load("1=1", (), order_by="id DESC", limit=1)
                return last_trade[0]['id'] if last_trade else None
            return None
    
    # ========== 操作记录 (Operations) ==========
    
    def load_operations_by_trade(
        self, 
        trade_id: int
    ) -> List[Dict[str, Any]]:
        """
        加载指定交易的所有操作记录
        
        Args:
            trade_id: 交易ID
        
        Returns:
            操作记录列表，按日期排序
        """
        model = self._get_operations_model()
        condition = "trade_id = %s"
        params = (trade_id,)
        return model.load(condition, params, order_by="date ASC")
    
    def load_operations_by_date_range(
        self,
        start_date: str,
        end_date: str,
        operation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        加载指定日期范围的操作记录
        
        Args:
            start_date: 起始日期
            end_date: 结束日期
            operation_type: 操作类型 ('buy', 'sell', 'add')
        
        Returns:
            操作记录列表
        """
        model = self._get_operations_model()
        
        if operation_type:
            condition = "date >= %s AND date <= %s AND type = %s"
            params = (start_date, end_date, operation_type)
        else:
            condition = "date >= %s AND date <= %s"
            params = (start_date, end_date)
        
        return model.load(condition, params, order_by="date ASC")
    
    def save_operation(self, data: Dict[str, Any]) -> bool:
        """
        保存操作记录
        
        Args:
            data: 操作数据，必须包含 'trade_id', 'type', 'date', 'price', 'amount'
        
        Returns:
            是否保存成功
        """
        required_fields = ['trade_id', 'type', 'date', 'price', 'amount']
        for field in required_fields:
            if field not in data:
                logger.error(f"操作数据缺少必要字段: {field}")
                return False
        
        model = self._get_operations_model()
        affected = model.insert([data])
        return affected > 0
    
    def save_operations_batch(self, data_list: List[Dict[str, Any]]) -> bool:
        """
        批量保存操作记录
        
        Args:
            data_list: 操作数据列表
        
        Returns:
            是否保存成功
        """
        if not data_list:
            return True
        
        required_fields = ['trade_id', 'type', 'date', 'price', 'amount']
        for data in data_list:
            for field in required_fields:
                if field not in data:
                    logger.error(f"操作数据缺少必要字段: {field}")
                    return False
        
        model = self._get_operations_model()
        affected = model.insert(data_list)
        return affected > 0
    
    # ========== 联合查询 ==========
    
    def load_trade_with_operations(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """
        加载交易及其所有操作记录
        
        Args:
            trade_id: 交易ID
        
        Returns:
            包含交易信息和操作列表的字典
        """
        trade = self.load_trade(trade_id)
        if not trade:
            return None
        
        operations = self.load_operations_by_trade(trade_id)
        
        return {
            'trade': trade,
            'operations': operations
        }
    
    def load_portfolio_summary(self, strategy: Optional[str] = None) -> Dict[str, Any]:
        """
        加载持仓汇总
        
        Args:
            strategy: 策略名称筛选
        
        Returns:
            持仓汇总信息
        """
        open_trades = self.load_open_trades(strategy)
        
        # 为每个交易加载操作记录
        portfolio = []
        for trade in open_trades:
            operations = self.load_operations_by_trade(trade['id'])
            portfolio.append({
                'trade': trade,
                'operations': operations
            })
        
        return {
            'total_positions': len(portfolio),
            'positions': portfolio
        }


__all__ = ['InvestmentDataService']

