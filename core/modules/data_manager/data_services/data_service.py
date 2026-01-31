"""
DataService - 跨 service 协调器

职责：
1. 管理各个子 Service（stock, macro, calendar, index, db_cache）
2. 统一访问入口（通过 data_mgr.stock / data_mgr.macro 等）
"""
from . import BaseDataService


class DataService:
    """
    DataService 主类，管理所有子 Service

    使用方式：
        data_service = DataService(data_manager)
        klines = data_service.stock.kline.load('000001.SZ')
        gdp = data_service.macro.load_gdp('2020Q1', '2024Q4')
        latest_date = data_service.calendar.get_latest_trading_date()
    """

    def __init__(self, data_manager):
        """
        初始化 DataService

        Args:
            data_manager: DataManager 实例
        """
        self.data_manager = data_manager

        # 初始化各个子 Service
        from .stock.stock_service import StockService
        from .macro.macro_service import MacroService
        from .calendar.calendar_service import CalendarService
        from .index.index_service import IndexService
        from .db_cache.db_cache_service import DbCacheService

        self.stock = StockService(data_manager)
        self.macro = MacroService(data_manager)
        self.calendar = CalendarService(data_manager)
        self.index = IndexService(data_manager)
        self.db_cache = DbCacheService(data_manager)
