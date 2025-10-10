#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tushare 数据源提供者 - 简化版本
只暴露一个 renew 方法，内部管理所有 renewer 实例
"""

import tushare as ts
import pandas as pd
from loguru import logger
import warnings
from datetime import datetime
import time

# 导入新的组件
from .config import TushareConfig
from .rate_limiter import RateLimiterManager
from utils.progress.progress_tracker import ProgressTrackerManager

# 导入各个 renewer 模块（直接导入具体文件，无需__init__.py）
from .renewers.stock_list.renewer import StockListRenewer
from .renewers.stock_list.config import CONFIG as STOCK_LIST_CONFIG
from .renewers.stock_kline.renewer import StockKlineRenewer
from .renewers.stock_kline.config import CONFIG as STOCK_KLINE_CONFIG
from .renewers.price_indexes.renewer import PriceIndexesRenewer
from .renewers.price_indexes.config import CONFIG as PRICE_INDEXES_CONFIG
from .renewers.lpr.renewer import LPRRenewer
from .renewers.lpr.config import CONFIG as LPR_CONFIG
# adj_factor 在 akshare 中完成，不在此处实现
from .renewers.corporate_finance.renewer import CorporateFinanceRenewer
from .renewers.corporate_finance.config import CONFIG as CORPORATE_FINANCE_CONFIG
from .renewers.gdp.renewer import GDPRenewer
from .renewers.gdp.config import CONFIG as GDP_CONFIG
from .renewers.shibor.renewer import ShiborRenewer
from .renewers.shibor.config import CONFIG as SHIBOR_CONFIG

# 导入存储和服务
from app.data_source.providers.tushare.main_service import TushareService
from app.data_source.providers.tushare.main_storage import TushareStorage

# 抑制tushare库的FutureWarning
warnings.filterwarnings('ignore', category=FutureWarning, module='tushare')


class Tushare:
    """Tushare 数据源提供者 - 简化版本"""
    
    def __init__(self, connected_db, is_verbose: bool = False):
        """
        初始化 Tushare 数据源
        
        Args:
            connected_db: 数据库连接
            is_verbose: 是否详细日志
        """
        self.db = connected_db
        self.storage = TushareStorage(connected_db)
        self.is_verbose = is_verbose

        # 初始化配置管理器
        self.config = TushareConfig()
        
        # 初始化API
        self.use_token()
        self.api = ts.pro_api()
        
        # 初始化限流器管理器
        self.rate_limiter_manager = RateLimiterManager()
        
        # 初始化进度跟踪器管理器
        self.progress_tracker_manager = ProgressTrackerManager()
        
        # 初始化各个 renewer 实例
        self._init_renewers()
        
        # 获取限流器实例（用于K线数据等传统方法）
        self.kline_rate_limiter = self.rate_limiter_manager.get_limiter(
            'K线数据',
            self.config.kline_rate_limit.max_per_minute,
            self.config.kline_rate_limit.buffer
        )
        
        self.corp_finance_rate_limiter = self.rate_limiter_manager.get_limiter(
            '企业财务数据',
            self.config.corp_finance_rate_limit.max_per_minute,
            self.config.corp_finance_rate_limit.buffer
        )
        
        # 线程局部 DB（用于多线程场景）
        import threading
        self._thread_local = threading.local()
        self._thread_dbs = []
        self._thread_dbs_lock = threading.Lock()

        self.stock_list_table = self.db.get_table_instance('stock_list')

    def load_filtered_stock_list(self):
        return self.stock_list_table.load_filtered_stock_list()


    def _init_renewers(self):
        """初始化所有 renewer 实例"""
        renewer_params = {
            'db': self.db,
            'api': self.api,
            'storage': self.storage,
            'is_verbose': self.is_verbose
        }
        
        self.stock_list_renewer = StockListRenewer(
            config=STOCK_LIST_CONFIG, **renewer_params
        )
        self.stock_kline_renewer = StockKlineRenewer(
            config=STOCK_KLINE_CONFIG, **renewer_params
        )
        self.price_indexes_renewer = PriceIndexesRenewer(
            config=PRICE_INDEXES_CONFIG, **renewer_params
        )
        self.lpr_renewer = LPRRenewer(
            config=LPR_CONFIG, **renewer_params
        )
        # adj_factor 在 akshare 中完成，不在此处实现
        self.corporate_finance_renewer = CorporateFinanceRenewer(
            config=CORPORATE_FINANCE_CONFIG, **renewer_params
        )
        self.gdp_renewer = GDPRenewer(
            config=GDP_CONFIG, **renewer_params
        )
        self.shibor_renewer = ShiborRenewer(
            config=SHIBOR_CONFIG, **renewer_params
        )
    
    # ================================ 主要API ================================
    
    async def renew(self, latest_market_open_day: str = None, stock_list: list = None):
        """
        Tushare 数据源统一更新入口
        内部处理所有 Tushare 相关的数据更新
        
        Args:
            latest_market_open_day: 最新市场开放日
            stock_list: 股票列表（用于依赖关系）
            
        Returns:
            更新结果
        """
        if latest_market_open_day is None:
            raise ValueError("latest_market_open_day 参数不能为 None")
        
        logger.info("🔄 开始更新 Tushare 数据源")
        
        try:
            # 更新K线数据（使用新的stock_kline renewer）
            # logger.info("📈 更新股票K线数据...")
            # self.stock_kline_renewer.renew(latest_market_open_day, stock_list)

            # 更新企业财务数据（依赖股票列表）
            # logger.info("💼 更新企业财务数据...")
            # self.corporate_finance_renewer.renew(latest_market_open_day, stock_list)
            
            # 更新宏观经济数据（独立并行）
            logger.info("🌍 更新宏观经济数据...")
            self.price_indexes_renewer.renew(latest_market_open_day)
            # self.lpr_renewer.renew(latest_market_open_day)
            # self.gdp_renewer.renew(latest_market_open_day)
            # self.shibor_renewer.renew(latest_market_open_day)

            # logger.info("✅ Tushare 数据源更新完成")
            # return True
            
        except Exception as e:
            logger.error(f"❌ Tushare 数据源更新失败: {e}")
            raise
    
    # ================================ 认证相关 ================================
    
    def get_token(self):
        """获取 Tushare token"""
        try:
            with open(self.config.auth_token_file, 'r') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"Token file not found at: {self.config.auth_token_file}. Please create file with token string inside.")

    def use_token(self):
        """设置 Tushare token"""
        ts.set_token(self.get_token())
    
    # ================================ 传统方法（保留用于向后兼容） ================================
    
    async def get_latest_market_open_day(self):
        """获取最新市场开放日"""
        return TushareService.get_latest_market_open_day(self.api)
    