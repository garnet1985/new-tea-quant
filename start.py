#!/usr/bin/env python3
"""
Debug测试文件 - 验证代码是否生效
"""
import sys
import os
from loguru import logger
from crawler.providers.tushare.query import TushareQuery
from crawler.db.db_manager import DatabaseManager

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class App:
    def __init__(self):
        self.db = DatabaseManager()
        # self.tushare = TushareQuery()
        # self.setup_database()
        # self.setup_data_source()
        # self.run_strategy_simulations()
        # self.scan_opportunities()

    def setup_database(self):
        print("setup_database")
        # step 1: set up database
        self.db.connect_sync()
        # 2. create db if not exists
        self.db.create_db()
        # 3. create tables if not exists
        self.db.create_tables()

    def setup_data_source(self):
        # step 1: set up tushare
        # self.tushare.setup_tushare()
        # step 2: renew data
        # self.tushare.renew_data()
        pass

    def run_strategy_simulations(self):
        # step 1: run registered strategy simulations
        # self.strategy.run_simulations()
        pass


    def scan_opportunities(self):
        # step 1: scan opportunities and show report
        # self.strategy.scan_opportunities()
        pass


    # the main entry point
def main():
    app = App();

    # step 1: set up database
    app.setup_database()

    # step 2: set up data source
    app.setup_data_source()

    # step 3: run registered strategy simulations
    app.run_strategy_simulations()

    # step 4: scan opportunities and show report
    app.scan_opportunities()

# def setup_database():
    
#     db = DatabaseManager()
#     # 1. connect to db
#     db.connect_sync()
#     # 2. create db if not exists
#     db.create_db()
#     # 3. create tables if not exists
#     db.create_tables()
#     # 4. create indexes if not exists
#     db.create_indexes()

# t = TushareQuery()
# print(t.last_market_open_day)



# step 2: set up data source
    # 1. set up tushare
    # 2. renew data

# step 3: run registered strategy simulations

# step 4: scan opportunities and show report

if __name__ == "__main__":
    logger.info("🚀 启动股票分析应用...")
    main()