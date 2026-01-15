"""
UI/中转数据服务

包含：
- 投资操作记录（买入、卖出、持仓）
- 扫描结果（待实现）
- 策略运行日志（待实现）
"""

from typing import Optional
from .. import BaseDataService
from .investment.investment_data_service import InvestmentDataService


class UiTransitDataService(BaseDataService):
    """
    UI/中转数据的统一接口
    
    当前作为转发器，未来可以添加大类内的组合查询方法。
    """
    
    def __init__(self, data_manager):
        super().__init__(data_manager)
        self.investment_service: Optional[InvestmentDataService] = None
        self.scan_result_service = None  # 待实现
    
    def initialize(self):
        """初始化所有子 Service"""
        self.investment_service = InvestmentDataService(self.data_manager)
        # self.scan_result_service = ScanResultDataService(self.data_manager)
    
    # ========== 转发方法 ==========
    
    # Investment 相关
    def load_trade(self, *args, **kwargs):
        """转发到 InvestmentDataService"""
        return self.investment_service.load_trade(*args, **kwargs)
    
    def load_trades_by_stock(self, *args, **kwargs):
        """转发到 InvestmentDataService"""
        return self.investment_service.load_trades_by_stock(*args, **kwargs)
    
    def load_open_trades(self, *args, **kwargs):
        """转发到 InvestmentDataService"""
        return self.investment_service.load_open_trades(*args, **kwargs)
    
    def load_operations_by_trade(self, *args, **kwargs):
        """转发到 InvestmentDataService"""
        return self.investment_service.load_operations_by_trade(*args, **kwargs)
    
    def load_trade_with_operations(self, *args, **kwargs):
        """转发到 InvestmentDataService"""
        return self.investment_service.load_trade_with_operations(*args, **kwargs)
    
    def load_portfolio_summary(self, *args, **kwargs):
        """转发到 InvestmentDataService"""
        return self.investment_service.load_portfolio_summary(*args, **kwargs)
    
    def save_trade(self, *args, **kwargs):
        """转发到 InvestmentDataService"""
        return self.investment_service.save_trade(*args, **kwargs)
    
    def save_operation(self, *args, **kwargs):
        """转发到 InvestmentDataService"""
        return self.investment_service.save_operation(*args, **kwargs)


__all__ = ['UiTransitDataService']

