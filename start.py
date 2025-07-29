#!/usr/bin/env python3
"""
股票分析应用主入口
"""
import sys
import os
from loguru import logger
import asyncio

from utils.db.db_manager import DatabaseManager
from app.data_source.providers.tushare.main import Tushare
from app.analyser.strategy import StrategyManager


# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class App:
    def __init__(self):
        self.db = DatabaseManager()
        self.data_source = Tushare(self.db)
        self.strategy = StrategyManager(self.db)

    async def renew_data(self):
        """更新股票数据"""
        await self.data_source.renew_data()
    
    def scan_strategies(self):
        self.strategy.scan_all_strategies()
        

async def main():
    app = App()
    
    # await app.renew_data()

    app.scan_strategies()


if __name__ == "__main__":
    logger.info("🚀 启动股票分析应用...")
    asyncio.run(main())
