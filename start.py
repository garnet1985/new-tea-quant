#!/usr/bin/env python3
"""
股票分析应用主入口
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
        self.db.initialize()
        self.data_source = Tushare(self.db)

    def renew_data(self):
        """更新股票数据"""
        
        # 添加数据更新完成后的回调函数
        # self.db.add_global_callback(self.on_data_renew_complete)
        
        self.data_source.renew_data()
    
    def on_data_renew_complete(self):
        """数据更新完成后的回调函数"""
        logger.info("🎉 数据更新完成！")
        # 这里可以添加后续任务，如策略分析、报告生成等

def main():
    app = App()

    app.renew_data();

    # 更新数据（可选）
    # app.renew_data()

if __name__ == "__main__":
    logger.info("🚀 启动股票分析应用...")
    main()