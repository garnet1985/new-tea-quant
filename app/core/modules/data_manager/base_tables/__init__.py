"""
Base Tables Models - 所有基础表的 Model 类

⚠️ 警告：本模块仅供 DataManager 内部使用，不应被外部代码直接导入！

设计原则：
- 所有 Model 类都是 DataManager 的内部实现细节
- 外部代码应通过 DataManager 的 DataService 层访问数据
- 直接导入和使用 Model 会破坏封装性，导致代码耦合

正确的使用方式：
    # ✅ 正确：通过 DataManager 访问
    from app.core.modules.data_manager import DataManager
    
    data_mgr = DataManager()
    data_mgr.initialize()
    klines = data_mgr.stock.kline.load('000001.SZ', start_date='20200101')
    
    # ❌ 错误：直接导入 Model（不要这样做）
    # from app.core.modules.data_manager.base_tables import StockKlineModel
    # kline_model = StockKlineModel()
    # klines = kline_model.load_by_date_range(...)

每个表都有自己的 Model 类，继承自 DbBaseModel，提供：
- 单表的 CRUD 操作
- 常用的业务查询方法
- 批量操作方法

这些 Model 仅由 DataManager 和 DataService 内部使用。
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
from .investment_trades.model import InvestmentTradesModel
from .investment_operations.model import InvestmentOperationsModel
from .stock_index_indicator.model import StockIndexIndicatorModel
from .stock_index_indicator_weight.model import StockIndexIndicatorWeightModel
from .system_cache.model import SystemCacheModel
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
    'InvestmentTradesModel',
    'InvestmentOperationsModel',
    'StockIndexIndicatorModel',
    'StockIndexIndicatorWeightModel',
    'SystemCacheModel',
    'TagDefinitionModel',
    'TagScenarioModel',
    'TagValueModel',
]

