#!/usr/bin/env python3
"""
重新创建stock_kline表以应用新的schema
"""
import sys
import os
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import get_sync_db_manager

def recreate_stock_kline_table():
    """重新创建stock_kline表"""
    logger.info("🔄 开始重新创建stock_kline表...")
    
    # 获取数据库管理器并初始化
    db = get_sync_db_manager()
    db.initialize()
    
    try:
        # 删除现有表
        logger.info("删除现有stock_kline表...")
        db.execute_sync_query("DROP TABLE IF EXISTS stock_kline")
        
        # 重新创建表
        logger.info("重新创建stock_kline表...")
        stock_kline_table = db.get_table_instance('stock_kline', 'base')
        success = stock_kline_table.create_table()
        
        if success:
            logger.info("✅ stock_kline表重新创建成功！")
            
            # 显示表结构
            logger.info("📋 新的表结构:")
            result = db.execute_sync_query("DESCRIBE stock_kline")
            for row in result:
                logger.info(f"  {row['Field']} - {row['Type']} - {row['Key']}")
                
        else:
            logger.error("❌ stock_kline表重新创建失败！")
            
    except Exception as e:
        logger.error(f"重新创建表时出错: {e}")

if __name__ == "__main__":
    recreate_stock_kline_table() 