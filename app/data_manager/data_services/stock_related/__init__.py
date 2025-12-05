"""
股票相关数据服务

包含：
- 股票基础数据（K线、标签、列表）
- 财务数据（利润表、现金流、资产负债表）
- 行业数据（待实现）
"""

from typing import Optional, Dict, Any
from .. import BaseDataService
from .stock.stock_data_service import StockDataService
from .corporate_finance.corporate_finance_data_service import CorporateFinanceDataService


class StockRelatedDataService(BaseDataService):
    """
    股票相关数据的统一接口
    
    当前作为转发器，未来可以添加大类内的组合查询方法，例如：
    - load_stock_with_finance(): K线 + 财务数据
    - load_stock_with_labels(): K线 + 标签
    - load_stock_full_context(): 股票全量上下文
    """
    
    def __init__(self, data_manager):
        super().__init__(data_manager)
        self.stock_service: Optional[StockDataService] = None
        self.finance_service: Optional[CorporateFinanceDataService] = None
        self.industry_service = None  # 待实现
    
    def initialize(self):
        """初始化所有子 Service"""
        self.stock_service = StockDataService(self.data_manager)
        self.finance_service = CorporateFinanceDataService(self.data_manager)
        # self.industry_service = IndustryDataService(self.data_manager)
    
    # ========== 转发方法 ==========
    
    # Stock 相关
    def load_stock_list(self, *args, **kwargs):
        """转发到 StockDataService"""
        return self.stock_service.load_stock_list(*args, **kwargs)
    
    def load_kline(self, *args, **kwargs):
        """转发到 StockDataService"""
        return self.stock_service.load_kline(*args, **kwargs)
    
    def load_labels(self, *args, **kwargs):
        """转发到 StockDataService"""
        return self.stock_service.load_labels(*args, **kwargs)
    
    # Finance 相关
    def load_financials(self, *args, **kwargs):
        """转发到 CorporateFinanceDataService"""
        return self.finance_service.load_financials(*args, **kwargs)
    
    def load_financials_by_category(self, *args, **kwargs):
        """转发到 CorporateFinanceDataService"""
        return self.finance_service.load_financials_by_category(*args, **kwargs)
    
    def load_financials_trend(self, *args, **kwargs):
        """转发到 CorporateFinanceDataService"""
        return self.finance_service.load_financials_trend(*args, **kwargs)
    
    def load_latest_financials(self, *args, **kwargs):
        """转发到 CorporateFinanceDataService"""
        return self.finance_service.load_latest_financials(*args, **kwargs)
    
    # ========== 未来的组合查询方法（示例） ==========
    
    def load_stock_with_finance(self, ts_code: str, date: str, quarter: str) -> Dict[str, Any]:
        """
        预设组合：K线 + 财务数据
        
        如果未来发现这个组合高频使用，可以用 JOIN 优化。
        当前实现：分别查询后组装（依赖缓存保证性能）
        
        Args:
            ts_code: 股票代码
            date: 交易日期
            quarter: 财务季度
        """
        result = {
            'kline': self.stock_service.load_kline(ts_code, date),
            'finance': self.finance_service.load_financials(ts_code, quarter)
        }
        return result
    
    def load_stock_with_labels(self, ts_code: str, date: str) -> Dict[str, Any]:
        """
        预设组合：K线 + 标签
        """
        result = {
            'kline': self.stock_service.load_kline(ts_code, date),
            'labels': self.stock_service.load_labels(ts_code, date)
        }
        return result


__all__ = ['StockRelatedDataService']

