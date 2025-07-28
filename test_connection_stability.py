#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试数据库连接稳定性
"""

from loguru import logger
from utils.db.db_manager import get_sync_db_manager
from app.data_source.providers.tushare.main import Tushare

def test_connection_stability():
    """测试数据库连接稳定性"""
    logger.info("🧪 测试数据库连接稳定性")
    
    try:
        # 初始化
        db = get_sync_db_manager()
        tushare = Tushare(db)
        tushare.latest_market_open_day = tushare.service.get_latest_market_open_day(tushare.api)
        
        # 获取股票数据
        stock_data = tushare.renew_stock_index(is_force=False)
        
        if stock_data is not None and not stock_data.empty:
            # 测试多只股票，增加并发压力
            test_stocks = stock_data.head(3)
            stock_list = []
            for _, row in test_stocks.iterrows():
                ts_code = row['ts_code']
                code, market = ts_code.split('.')
                stock_list.append((code, market))
            
            logger.info(f"测试股票数量: {len(stock_list)}")
            
            # 生成任务
            jobs = tushare.service.generate_kline_renew_jobs(
                stock_list,
                tushare.latest_market_open_day,
                tushare.storage
            )
            
            # 执行任务
            logger.info("开始执行K线数据获取...")
            stats = tushare.execute_stock_kline_renew_jobs(jobs)
            
            logger.info("✅ 连接稳定性测试完成")
            logger.info(f"执行统计: {stats}")
            
            # 检查是否有连接错误
            if stats['failed_jobs'] == 0:
                logger.info("🎉 没有连接错误，测试成功！")
            else:
                logger.warning(f"⚠️ 有 {stats['failed_jobs']} 个任务失败")
            
        else:
            logger.warning("没有获取到股票数据")
            
    except Exception as e:
        logger.error(f"测试失败: {e}")
        raise

if __name__ == "__main__":
    test_connection_stability() 