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

    async def renew_data(self, actions: Optional[list] = None):
        tu = self.sources['tushare']
        ak = self.sources['akshare']

        # 先获取最新交易日
        self.latest_market_open_day = await tu.get_latest_market_open_day()
        logger.info(f"🔍 最新交易日: {self.latest_market_open_day}")
        
        # 动作选择
        actions = actions or [
            'stock_index',
            'stock_k_lines',
            'ak_adj_factors',
            'price_indexes', 'lpr', 'gdp', 'shibor',
            'stock_index_indicator', 'stock_index_indicator_weight',
            'industry_capital_flow', 'corporate_finance'
        ]

        # 然后更新股票指数
        if 'stock_index' in actions:
            self.latest_stock_index = tu.renew_stock_index(self.latest_market_open_day)


        # renew jobs:

        if 'stock_k_lines' in actions:
            await tu.renew_stock_k_lines(self.latest_market_open_day, self.latest_stock_index)
        
        if 'ak_adj_factors' in actions:
            ak.inject_dependency(tu).renew_stock_k_line_factors(self.latest_market_open_day, self.latest_stock_index)

        # macro economic indexes
        if 'price_indexes' in actions:
            tu.renew_price_indexes(self.latest_market_open_day)

        if 'lpr' in actions:
            tu.renew_LPR(self.latest_market_open_day)

        if 'gdp' in actions:
            tu.renew_GDP(self.latest_market_open_day)

        if 'shibor' in actions:
            tu.renew_Shibor(self.latest_market_open_day)

        # stock index indicators and weights
        if 'stock_index_indicator' in actions:
            tu.renew_stock_index_indicator(self.latest_market_open_day)
        if 'stock_index_indicator_weight' in actions:
            tu.renew_stock_index_indicator_weight(self.latest_market_open_day)

        # industry capital flow
        if 'industry_capital_flow' in actions:
            tu.renew_industry_capital_flow(self.latest_market_open_day)

        # corporate financial data
        if 'corporate_finance' in actions:
            tu.renew_corporate_finance(self.latest_market_open_day)
