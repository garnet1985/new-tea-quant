"""
Data Service 子模块

说明：
- 用于封装跨表 / 领域级的数据访问逻辑
- 由 DataManager 统一创建和管理

业务领域分类：
- StockDataService        - 股票数据（列表、K线、标签、复权因子等）
- CorporateFinanceDataService - 财务数据
- MacroDataService        - 宏观经济（GDP、CPI、Shibor、LPR 等）
- InvestmentDataService   - 投资交易（交易记录、操作记录）
- IndustryDataService     - 行业资金流
- IndexDataService        - 指数指标
- MetaDataService         - 元信息
- <Strategy>DataService   - 策略相关数据（策略表 + 基础表联动）
"""

from typing import Dict, Any


class BaseDataService:
    """
    DataService 基类
    
    所有 DataService 都应该继承此类，提供统一的接口规范
    """

    def __init__(self, data_manager: Any):
        """
        初始化 DataService
        
        Args:
            data_manager: DataManager 实例，用于获取 Model 和数据库访问
        """
        self.data_manager = data_manager


# 导出 DataService 主类
from .data_service import DataService

__all__ = [
    "BaseDataService",
    "DataService",
]
