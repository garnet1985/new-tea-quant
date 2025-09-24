from loguru import logger
from app.data_source.providers.tushare.main import Tushare
from app.data_source.providers.akshare.main import AKShare
from app.data_source.providers.akshare.main_storage import AKShareStorage
from typing import List, Dict, Optional, Union
import pandas as pd

class DataSourceManager:
    def __init__(self, connected_db, is_verbose: bool = False):
        self.db = connected_db
        self.is_verbose = is_verbose

        self.sources = {
            'tushare': Tushare(connected_db, is_verbose),
            'akshare': AKShare(connected_db, is_verbose),
        }

        # 初始化复权服务
        self.adj_factor_storage = AKShareStorage(connected_db)

        # global data memory cache
        self.latest_market_open_day = None
        self.latest_stock_index = None

    def get_source(self, source_name: str):
        return self.sources[source_name]()

    async def renew_data(self):
        tu = self.sources['tushare']
        ak = self.sources['akshare']

        # 先获取最新交易日
        self.latest_market_open_day = await tu.get_latest_market_open_day()
        logger.info(f"🔍 最新交易日: {self.latest_market_open_day}")
        
        # 然后更新股票指数
        self.latest_stock_index = tu.renew_stock_index(self.latest_market_open_day)
        # logger.info(f"🔍 股票清单更新完成")

        # await tu.renew_stock_k_lines(self.latest_market_open_day, self.latest_stock_index)
        
        # ak.inject_dependency(tu).renew_stock_k_line_factors(self.latest_market_open_day, self.latest_stock_index)

        # macro economic indexes
        tu.renew_price_indexes(self.latest_market_open_day)

        tu.renew_interest_rates(self.latest_market_open_day)

        # below are not implemented yet
        # tu.renew_global_economic_data()
        # tu.renew_corporate_finance_data()