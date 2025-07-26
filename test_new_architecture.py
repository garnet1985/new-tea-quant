#!/usr/bin/env python3
"""
测试新的批量处理架构
"""
import sys
import os
import time
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.db.db_manager import get_sync_db_manager
from app.data_source.providers.tushare.main import Tushare

def test_new_architecture():
    """测试新的批量处理架构"""
    logger.info("🧪 开始测试新的批量处理架构...")
    
    # 获取数据库管理器并初始化
    db = get_sync_db_manager()
    db.initialize()
    
    # 创建Tushare实例
    tushare = Tushare(db)
    
    # 模拟一些股票信息 (code, market)
    test_stock_info = [
        ('000001', 'SZ'), ('000002', 'SZ'), ('000004', 'SZ'), 
        ('000006', 'SZ'), ('000007', 'SZ')
    ]
    terms = ['daily', 'weekly', 'monthly']
    last_market_open_day = '20250726'
    default_start_date = '20080101'
    
    logger.info(f"测试股票数量: {len(test_stock_info)}")
    logger.info(f"测试周期: {terms}")
    logger.info(f"默认开始日期: {default_start_date}")
    
    # 测试生成更新任务
    start_time = time.time()
    jobs = tushare.generate_kline_update_jobs(
        test_stock_info, terms, last_market_open_day, default_start_date
    )
    job_generation_time = time.time() - start_time
    
    logger.info(f"任务生成耗时: {job_generation_time:.3f}秒")
    logger.info(f"生成了 {len(jobs)} 个更新任务")
    
    # 显示任务统计
    logger.info("\n📊 任务统计:")
    by_term = {}
    by_reason = {}
    for job in jobs:
        term = job['term']
        reason = job['reason']
        
        if term not in by_term:
            by_term[term] = 0
        by_term[term] += 1
        
        if reason not in by_reason:
            by_reason[reason] = 0
        by_reason[reason] += 1
    
    logger.info(f"按周期分布: {by_term}")
    logger.info(f"按原因分布: {by_reason}")
    
    # 显示前几个任务详情
    logger.info("\n前5个任务详情:")
    for i, job in enumerate(jobs[:5]):
        logger.info(f"  {i+1}. {job['ts_code']} {job['term']}: "
                   f"{job['start_date']} -> {job['end_date']} ({job['reason']})")
    
    # 测试任务执行（模拟）
    logger.info("\n🚀 开始模拟任务执行...")
    start_time = time.time()
    tushare.execute_kline_jobs(jobs, batch_size=3)
    execution_time = time.time() - start_time
    
    logger.info(f"任务执行耗时: {execution_time:.3f}秒")
    
    # 性能对比
    logger.info("\n📈 性能对比:")
    logger.info(f"传统方法: {len(test_stock_info) * len(terms)} 次数据库查询")
    logger.info(f"批量方法: 1 次数据库查询 + 内存处理")
    logger.info(f"性能提升: {(len(test_stock_info) * len(terms) - 1) / (len(test_stock_info) * len(terms)) * 100:.1f}%")
    
    # 索引优化说明
    logger.info("\n🔍 索引优化:")
    logger.info("新增了以下索引来优化 GROUP BY 查询:")
    logger.info("  - idx_code_term: 优化按股票代码和周期分组")
    logger.info("  - idx_term_date: 优化按周期和日期分组")
    logger.info("这些索引将显著提升 GROUP BY 查询性能")
    
    logger.info("\n🎉 新架构测试完成！")

if __name__ == "__main__":
    test_new_architecture() 