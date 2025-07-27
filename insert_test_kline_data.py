#!/usr/bin/env python3
"""
为stock_kline表插入测试数据
"""
import sys
import os
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import get_sync_db_manager

def insert_test_kline_data():
    """插入stock_kline测试数据"""
    logger.info("📝 开始插入stock_kline测试数据...")
    
    # 获取数据库管理器并初始化
    db = get_sync_db_manager()
    db.initialize()
    
    # 获取stock_kline表实例
    stock_kline_table = db.get_table_instance('stock_kline', 'base')
    
    # 测试数据
    test_data = [
        # Daily 数据
        {
            'code': '000001',
            'market': 'SZ',
            'term': 'daily',
            'date': '20250725',
            'open': 12.50,
            'close': 12.80,
            'highest': 12.95,
            'lowest': 12.45,
            'priceChangeDelta': 0.30,
            'priceChangeRateDelta': 2.40,
            'preClose': 12.50,
            'volume': 1500000,
            'amount': 19000000.00
        },
        {
            'code': '000002',
            'market': 'SZ',
            'term': 'daily',
            'date': '20250725',
            'open': 15.20,
            'close': 15.60,
            'highest': 15.75,
            'lowest': 15.15,
            'priceChangeDelta': 0.40,
            'priceChangeRateDelta': 2.63,
            'preClose': 15.20,
            'volume': 2000000,
            'amount': 31000000.00
        },
        {
            'code': '000004',
            'market': 'SZ',
            'term': 'daily',
            'date': '20250725',
            'open': 8.80,
            'close': 9.10,
            'highest': 9.25,
            'lowest': 8.75,
            'priceChangeDelta': 0.30,
            'priceChangeRateDelta': 3.41,
            'preClose': 8.80,
            'volume': 800000,
            'amount': 7200000.00
        },
        # Weekly 数据
        {
            'code': '000001',
            'market': 'SZ',
            'term': 'weekly',
            'date': '20250725',
            'open': 12.20,
            'close': 12.80,
            'highest': 13.10,
            'lowest': 12.00,
            'priceChangeDelta': 0.60,
            'priceChangeRateDelta': 4.92,
            'preClose': 12.20,
            'volume': 7500000,
            'amount': 95000000.00
        },
        {
            'code': '000002',
            'market': 'SZ',
            'term': 'weekly',
            'date': '20250725',
            'open': 14.80,
            'close': 15.60,
            'highest': 15.90,
            'lowest': 14.60,
            'priceChangeDelta': 0.80,
            'priceChangeRateDelta': 5.41,
            'preClose': 14.80,
            'volume': 10000000,
            'amount': 155000000.00
        },
        {
            'code': '000004',
            'market': 'SZ',
            'term': 'weekly',
            'date': '20250725',
            'open': 8.50,
            'close': 9.10,
            'highest': 9.40,
            'lowest': 8.40,
            'priceChangeDelta': 0.60,
            'priceChangeRateDelta': 7.06,
            'preClose': 8.50,
            'volume': 4000000,
            'amount': 36000000.00
        },
        # Monthly 数据
        {
            'code': '000001',
            'market': 'SZ',
            'term': 'monthly',
            'date': '20250725',
            'open': 11.80,
            'close': 12.80,
            'highest': 13.50,
            'lowest': 11.50,
            'priceChangeDelta': 1.00,
            'priceChangeRateDelta': 8.47,
            'preClose': 11.80,
            'volume': 30000000,
            'amount': 380000000.00
        },
        {
            'code': '000002',
            'market': 'SZ',
            'term': 'monthly',
            'date': '20250725',
            'open': 14.20,
            'close': 15.60,
            'highest': 16.20,
            'lowest': 14.00,
            'priceChangeDelta': 1.40,
            'priceChangeRateDelta': 9.86,
            'preClose': 14.20,
            'volume': 40000000,
            'amount': 620000000.00
        },
        {
            'code': '000004',
            'market': 'SZ',
            'term': 'monthly',
            'date': '20250725',
            'open': 8.00,
            'close': 9.10,
            'highest': 9.60,
            'lowest': 7.80,
            'priceChangeDelta': 1.10,
            'priceChangeRateDelta': 13.75,
            'preClose': 8.00,
            'volume': 16000000,
            'amount': 144000000.00
        }
    ]
    
    try:
        # 插入测试数据
        logger.info(f"插入 {len(test_data)} 条测试数据...")
        for i, data in enumerate(test_data, 1):
            ts_code = f"{data['code']}.{data['market']}"
            logger.info(f"插入第 {i} 条数据: {ts_code} {data['term']} {data['date']}")
            stock_kline_table.insert_one(data)
        
        logger.info("✅ 测试数据插入成功！")
        
        # 验证插入的数据
        logger.info("📋 验证插入的数据:")
        result = stock_kline_table.find_many("1=1", ())
        for row in result:
            ts_code = f"{row['code']}.{row['market']}"
            logger.info(f"  {ts_code} {row['term']} {row['date']}: "
                       f"开盘{row['open']} 收盘{row['close']} 最高{row['highest']} 最低{row['lowest']}")
        
        # 显示数据统计
        count = stock_kline_table.count("1=1", ())
        logger.info(f"📊 stock_kline表总记录数: {count}")
        
    except Exception as e:
        logger.error(f"插入测试数据失败: {e}")

if __name__ == "__main__":
    insert_test_kline_data() 