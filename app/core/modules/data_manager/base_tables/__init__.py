"""
Base Tables Models - 所有基础表的 Model 类

每个表都有自己的 Model 类，继承自 DbBaseModel，提供：
- 单表的 CRUD 操作
- 常用的业务查询方法
- 批量操作方法

使用示例：
    from app.core.modules.data_manager.base_tables.stock_kline.model import StockKlineModel
    from app.core.infra.db import DatabaseManager
    
    db = DatabaseManager()
    db.initialize()
    
    kline_model = StockKlineModel(db)
    klines = kline_model.load_by_date_range('000001.SZ', '20200101', '20201231')
"""

# 导出所有 Model 类
from .stock_kline.model import StockKlineModel
from .stock_list.model import StockListModel
# adj_factor 模块已移除，使用 adj_factor_event 替代
# from .adj_factor.model import AdjFactorModel
from .adj_factor_event.model import AdjFactorEventModel
from .gdp.model import GdpModel
from .price_indexes.model import PriceIndexesModel
from .shibor.model import ShiborModel
from .lpr.model import LprModel
from .corporate_finance.model import CorporateFinanceModel
from .stock_labels.model import StockLabelsModel
from .investment_trades.model import InvestmentTradesModel
from .investment_operations.model import InvestmentOperationsModel
from .stock_index_indicator.model import StockIndexIndicatorModel
from .stock_index_indicator_weight.model import StockIndexIndicatorWeightModel
from .meta_info.model import MetaInfoModel
from .tag_definition.model import TagDefinitionModel
from .tag_scenario.model import TagScenarioModel
from .tag_value.model import TagValueModel

__all__ = [
    'StockKlineModel',
    'StockListModel',
    # 'AdjFactorModel',  # 已移除，使用 adj_factor_event 替代
    'AdjFactorEventModel',
    'GdpModel',
    'PriceIndexesModel',
    'ShiborModel',
    'LprModel',
    'CorporateFinanceModel',
    'StockLabelsModel',
    'InvestmentTradesModel',
    'InvestmentOperationsModel',
    'StockIndexIndicatorModel',
    'StockIndexIndicatorWeightModel',
    'MetaInfoModel',
    'TagDefinitionModel',
    'TagScenarioModel',
    'TagValueModel',
]

