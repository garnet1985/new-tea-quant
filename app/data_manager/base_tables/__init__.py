"""
Base Tables Models - 所有基础表的 Model 类

每个表都有自己的 Model 类，继承自 BaseTableModel，提供：
- 单表的 CRUD 操作
- 常用的业务查询方法
- 批量操作方法

使用示例：
    from app.data_manager.base_tables.stock_kline.model import StockKlineModel
    from utils.db.db_manager import DatabaseManager
    
    db = DatabaseManager()
    db.initialize()
    
    kline_model = StockKlineModel(db)
    klines = kline_model.load_by_date_range('000001.SZ', '20200101', '20201231')
"""

# 导出所有 Model 类
from .stock_kline.model import StockKlineModel
from .stock_list.model import StockListModel
from .adj_factor.model import AdjFactorModel
from .gdp.model import GdpModel
from .price_indexes.model import PriceIndexesModel
from .shibor.model import ShiborModel
from .lpr.model import LprModel
from .corporate_finance.model import CorporateFinanceModel
from .stock_labels.model import StockLabelsModel
from .investment_trades.model import InvestmentTradesModel
from .investment_operations.model import InvestmentOperationsModel
from .industry_capital_flow.model import IndustryCapitalFlowModel
from .stock_index_indicator.model import StockIndexIndicatorModel
from .stock_index_indicator_weight.model import StockIndexIndicatorWeightModel
from .meta_info.model import MetaInfoModel

__all__ = [
    'StockKlineModel',
    'StockListModel',
    'AdjFactorModel',
    'GdpModel',
    'PriceIndexesModel',
    'ShiborModel',
    'LprModel',
    'CorporateFinanceModel',
    'StockLabelsModel',
    'InvestmentTradesModel',
    'InvestmentOperationsModel',
    'IndustryCapitalFlowModel',
    'StockIndexIndicatorModel',
    'StockIndexIndicatorWeightModel',
    'MetaInfoModel',
]

