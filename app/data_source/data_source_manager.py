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

    def get_source(self, source_name: str):
        return self.sources[source_name]()

    def get_latest_market_open_day(self):
        """获取最新交易日"""
        tu = self.sources['tushare']
        return tu.get_latest_market_open_day()

    async def renew_data(self, latest_market_open_day: str):
        """
        协调不同数据源的更新
        负责管理 provider 之间的顺序和依赖关系
        
        Args:
            latest_market_open_day: 最新交易日 (YYYYMMDD格式)
        """
        tu = self.sources['tushare']
        
        # 1. 更新股票列表（替代 stock_index，排除北交所）
        tu.stock_list_renewer.renew(latest_market_open_day)

        # 2. 加载最新股票列表（排除规则在模型内处理）
        latest_stock_list = tu.load_filtered_stock_list()
        
        # 3. 更新 Tushare 数据源（包含K线、宏观经济、企业财务、股本信息等）
        await tu.renew(latest_market_open_day, latest_stock_list)

        # 4. 更新 AKShare 数据源
        ak = self.sources['akshare']
        ak.inject_dependency(tu)
        await ak.renew(latest_market_open_day, latest_stock_list)