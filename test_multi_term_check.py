#!/usr/bin/env python3
"""
测试不同周期的股票K线数据检查功能
"""
import sys
import os
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import get_sync_db_manager
from app.data_source.providers.tushare.storage import TushareStorage

def test_multi_term_check():
    """测试不同周期的股票K线数据检查功能"""
    logger.info("🧪 开始测试不同周期的股票K线数据检查功能...")
    
    # 获取数据库管理器并初始化
    db = get_sync_db_manager()
    db.initialize()
    
    # 创建存储实例
    storage = TushareStorage(db)
    
    # 测试不同的场景
    test_cases = [
        {
            'code': '000001',
            'term': 'daily',
            'last_market_open_day': '20250726',
            'description': '日线测试'
        },
        {
            'code': '000001', 
            'term': 'weekly',
            'last_market_open_day': '20250726',
            'description': '周线测试'
        },
        {
            'code': '000001',
            'term': 'monthly', 
            'last_market_open_day': '20250726',
            'description': '月线测试'
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
    test_multi_term_check() 