#!/usr/bin/env python3
"""
测试批量K线数据检查器的性能和功能
"""
import sys
import os
import time
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import get_sync_db_manager
from app.data_source.providers.tushare.storage import TushareStorage
from app.data_source.providers.tushare.batch_checker import BatchKlineChecker

def test_batch_checker_performance():
    """测试批量检查器的性能"""
    logger.info("🧪 开始测试批量K线数据检查器性能...")
    
    # 获取数据库管理器并初始化
    db = get_sync_db_manager()
    db.initialize()
    
    # 创建存储实例和批量检查器
    storage = TushareStorage(db)
    batch_checker = BatchKlineChecker(storage)
    
    # 模拟一些股票代码（实际应该有5000+）
    test_stock_codes = ['000001', '000002', '000004', '000006', '000007']
    terms = ['daily', 'weekly', 'monthly']
    last_market_open_day = '20250726'
    
    logger.info(f"测试股票数量: {len(test_stock_codes)}")
    logger.info(f"测试周期: {terms}")
    
    # 测试批量获取最新数据状态
    start_time = time.time()
    latest_data = batch_checker.get_all_latest_kline_data()
    batch_time = time.time() - start_time
    
    logger.info(f"批量查询耗时: {batch_time:.3f}秒")
    logger.info(f"获取到 {len(latest_data)} 只股票的数据状态")
    
    # 测试生成更新任务
    start_time = time.time()
    jobs = batch_checker.generate_update_jobs(test_stock_codes, terms, last_market_open_day)
    job_generation_time = time.time() - start_time
    
    logger.info(f"任务生成耗时: {job_generation_time:.3f}秒")
    logger.info(f"生成了 {len(jobs)} 个更新任务")
    
    # 显示任务统计
    stats = batch_checker.get_job_statistics(jobs)
    logger.info(f"任务统计: {stats}")
    
    # 显示前几个任务详情
    logger.info("\n前5个任务详情:")
    for i, job in enumerate(jobs[:5]):
        logger.info(f"  {i+1}. {job['code']} {job['term']}: {job['start_date']} -> {job['end_date']} ({job['reason']})")
    
    # 性能对比：传统方法 vs 批量方法
    logger.info("\n📊 性能对比:")
    logger.info(f"传统方法: {len(test_stock_codes) * len(terms)} 次数据库查询")
    logger.info(f"批量方法: 1 次数据库查询 + 内存处理")
    logger.info(f"性能提升: {(len(test_stock_codes) * len(terms) - 1) / (len(test_stock_codes) * len(terms)) * 100:.1f}%")
    
    # 模拟实际场景的性能估算
    real_stock_count = 5000
    real_terms = ['daily', 'weekly', 'monthly']
    
    logger.info(f"\n🚀 实际场景性能估算 (5000只股票):")
    logger.info(f"传统方法查询次数: {real_stock_count * len(real_terms)} = 15,000次")
    logger.info(f"批量方法查询次数: 1次")
    logger.info(f"预计性能提升: 99.99%")
    
    logger.info("\n🎉 批量检查器性能测试完成！")

if __name__ == "__main__":
    test_batch_checker_performance() 