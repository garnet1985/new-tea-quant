#!/usr/bin/env python3
"""
测试不同周期的股票K线数据检查功能（带示例数据）
"""
import sys
import os
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import get_sync_db_manager
from app.data_source.providers.tushare.storage import TushareStorage

def test_with_sample_data():
    """测试不同周期的股票K线数据检查功能（带示例数据）"""
    logger.info("🧪 开始测试不同周期的股票K线数据检查功能（带示例数据）...")
    
    # 获取数据库管理器并初始化
    db = get_sync_db_manager()
    db.initialize()
    
    # 创建存储实例
    storage = TushareStorage(db)
    
    # 插入一些示例数据
    sample_data = [
        # 日线数据：最新到 20250725
        {
            'code': '000001',
            'term': 'daily',
            'date': '20250725',
            'open': 10.50,
            'close': 10.60,
            'highest': 10.70,
            'lowest': 10.40,
            'priceChangeDelta': 0.10,
            'priceChangeRateDelta': 0.95,
            'preClose': 10.50,
            'volume': 1000000,
            'amount': 10600000.00
        },
        # 周线数据：最新到 20250721（周一）
        {
            'code': '000001',
            'term': 'weekly',
            'date': '20250721',
            'open': 10.30,
            'close': 10.60,
            'highest': 10.70,
            'lowest': 10.20,
            'priceChangeDelta': 0.30,
            'priceChangeRateDelta': 2.91,
            'preClose': 10.30,
            'volume': 5000000,
            'amount': 53000000.00
        },
        # 月线数据：最新到 20250701
        {
            'code': '000001',
            'term': 'monthly',
            'date': '20250701',
            'open': 10.00,
            'close': 10.60,
            'highest': 10.80,
            'lowest': 9.80,
            'priceChangeDelta': 0.60,
            'priceChangeRateDelta': 6.00,
            'preClose': 10.00,
            'volume': 20000000,
            'amount': 212000000.00
        }
    ]
    
    # 插入示例数据
    for data in sample_data:
        storage.stock_kline_table.insert_one(data)
    
    logger.info("✅ 示例数据插入完成")
    
    # 测试不同的场景
    test_cases = [
        {
            'code': '000001',
            'term': 'daily',
            'last_market_open_day': '20250726',
            'description': '日线测试（已有20250725数据）'
        },
        {
            'code': '000001', 
            'term': 'weekly',
            'last_market_open_day': '20250726',
            'description': '周线测试（已有20250721数据）'
        },
        {
            'code': '000001',
            'term': 'monthly', 
            'last_market_open_day': '20250726',
            'description': '月线测试（已有20250701数据）'
        }
    ]
    
    for test_case in test_cases:
        code = test_case['code']
        term = test_case['term']
        last_market_open_day = test_case['last_market_open_day']
        description = test_case['description']
        
        logger.info(f"\n📊 {description}")
        logger.info(f"股票代码: {code}")
        logger.info(f"周期: {term}")
        logger.info(f"最后交易日: {last_market_open_day}")
        
        try:
            should_renew, start_date, end_date = storage.should_renew_stock_kline(code, term, last_market_open_day)
            
            logger.info(f"是否需要更新: {should_renew}")
            if should_renew:
                logger.info(f"开始日期: {start_date}")
                logger.info(f"结束日期: {end_date}")
            else:
                logger.info("数据已是最新，无需更新")
                
        except Exception as e:
            logger.error(f"检查失败: {e}")
    
    logger.info("\n🎉 多周期K线数据检查功能测试完成！")

if __name__ == "__main__":
    test_with_sample_data() 