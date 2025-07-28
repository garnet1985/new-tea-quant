#!/usr/bin/env python3
"""
Debug测试文件 - 验证代码是否生效
"""
import sys
import os
from loguru import logger
from utils.db.db_manager import DatabaseManager

from app.data_source.providers.tushare.main import Tushare

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
        # step 1: set up database
        self.db.initialize()

    def renew_data(self):
        # 添加数据更新完成后的回调函数
        self.db.add_global_callback(self.on_data_renew_complete)
        
        data_source = Tushare(self.db)
        data_source.renew_data()
    
    def on_data_renew_complete(self):
        """数据更新完成后的回调函数"""
        logger.info("🎉 数据更新完成！开始执行后续任务...")
        
        # 这里可以添加你需要在数据更新完成后执行的函数
        # 例如：运行策略分析、生成报告等
        self.run_strategy_simulations()
        self.scan_opportunities()
        
        logger.info("✅ 后续任务执行完成")

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
    app.renew_data()

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