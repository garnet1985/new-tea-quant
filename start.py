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
from app.data_source.providers.tushare.main import Tushare
from app.analyzer import Analyzer


# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class App:
    def __init__(self):

        self.is_verbose = False
        # 1. 首先初始化数据库
        self.db = DatabaseManager(self.is_verbose)
        self.db.initialize()
        
        # 2. 然后创建数据源和策略管理器
        self.data_source = Tushare(self.db, self.is_verbose)
        self.analyzer = Analyzer(self.db, self.is_verbose)
        
        # 3. 初始化策略（这会注册表到数据库）
        self.analyzer.initialize()

    async def renew_data(self):
        """更新股票数据"""
        await self.data_source.renew_data()
    
    def scan_strategies(self):
        self.analyzer.scan_all_strategies()
        

async def main():
    app = App()
    
    # await app.renew_data()

    app.scan_strategies()


if __name__ == "__main__":
    logger.info("🚀 启动股票分析应用...")
    asyncio.run(main())
