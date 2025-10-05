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
        """
        协调不同数据源的更新
        负责管理 provider 之间的顺序和依赖关系
        """
        tu = self.sources['tushare']
        # 1. 获取最新交易日
        self.latest_market_open_day = await tu.get_latest_market_open_day()
        logger.info(f"🔍 最新交易日: {self.latest_market_open_day}")
        
        # 2. 更新股票指数（基础数据，其他模块依赖）
        tu.stock_index_renewer.renew(self.latest_market_open_day)

        self.latest_stock_index = tu.storage.load_stock_index()
        
        # 3. 更新 Tushare 数据源（包含K线、宏观经济、企业财务、股本信息等）
        await tu.renew(self.latest_market_open_day, self.latest_stock_index)


        # ak = self.sources['akshare']
        # ak.inject_dependency(tu)
        # await ak.renew(self.latest_market_open_day, self.latest_stock_index)