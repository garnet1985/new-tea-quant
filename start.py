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


# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class App:
    def __init__(self):
        self.is_verbose = False
        
        # 1. 首先初始化数据库（只初始化一次）
        self.db = DatabaseManager(self.is_verbose)
        self.db.initialize()
        
        # 2. 然后创建数据源和策略管理器（复用同一个数据库实例）
        self.data_source = DataSourceManager(self.db, self.is_verbose)
        self.analyzer = Analyzer(self.db, self.is_verbose)
        
        # 3. 初始化策略（这会注册表到数据库）
        self.analyzer.initialize()

    async def renew_data(self):
        """更新股票数据"""
        await self.data_source.renew_data()
    
    def simulate(self):
        # 使用run_daily_scan来同时执行扫描和测试
        self.analyzer.simulate()

    def scan(self):
        self.analyzer.scan()
        

def main():
    app = App()
    
    # app.renew_data()  # 数据更新仍为异步接口时再启用

    app.scan()

    # app.simulate()


if __name__ == "__main__":
    logger.info("🚀 启动股票分析应用...")
    main()
