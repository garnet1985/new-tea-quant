#!/usr/bin/env python3
"""
股票分析应用主入口
"""
import sys
import os
from loguru import logger
import asyncio

# 在导入其他模块之前设置警告抑制
from utils.warning_suppressor import setup_warning_suppression
setup_warning_suppression()

from utils.db.db_manager import DatabaseManager
from app.data_source.data_source_manager import DataSourceManager
from app.analyzer import Analyzer
from app.labeler import LabelerService
from utils.icon.icon_service import IconService


# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class App:
    def __init__(self):
        self.is_verbose = False
        
        # 1. 首先初始化数据库（只初始化一次）
        # 启用线程安全，支持多线程数据更新
        self.db = DatabaseManager(is_verbose=self.is_verbose, enable_thread_safety=True)
        self.db.initialize()
        
        # 2. 然后创建数据源和策略管理器（复用同一个数据库实例）
        self.data_source = DataSourceManager(self.db, self.is_verbose)
        self.analyzer = Analyzer(self.db, self.is_verbose)
        self.labeler = LabelerService(self.db)
        
        # 3. 初始化策略（这会注册表到数据库）
        self.analyzer.initialize()

    async def get_latest_market_open_day(self):
        """获取最新交易日"""
        return await self.data_source.get_latest_market_open_day()
    
    async def renew_data(self, latest_market_open_day: str):
        """更新股票数据"""
        await self.data_source.renew_data(latest_market_open_day)
    
    def renew_labels(self, last_market_open_day: str, force_update: bool = False):
        """更新股票标签"""
        self.labeler.renew(last_market_open_day, force_update=force_update)
    
    def simulate(self):
        # 使用run_daily_scan来同时执行扫描和测试
        self.analyzer.simulate()

    def scan(self):
        self.analyzer.scan()

    def analysis(self, session_id: str = None):
        """分析所有策略的模拟结果"""
        self.analyzer.analysis(session_id)
        

def main():
    app = App()
    
    # 1. 先获取最新交易日
    latest_market_open_day = asyncio.run(app.get_latest_market_open_day())

    logger.info(f"🔍 最新交易日: {latest_market_open_day}")
    
    # 2. 使用最新交易日更新股票数据
    # asyncio.run(app.renew_data(latest_market_open_day))
    
    # 3. 使用最新交易日更新股票标签（按频率更新）
    app.renew_labels(latest_market_open_day)

    # app.scan()

    # app.simulate()

    # app.analysis()


if __name__ == "__main__":
    main()
