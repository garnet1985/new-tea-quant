#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from utils.db.db_manager import get_sync_db_manager
from app.data_source.providers.tushare.storage import TushareStorage
from app.data_source.providers.tushare.optimized_fetcher import OptimizedKlineFetcher


def test_optimized_fetcher():
    """测试优化的批量获取器"""
    logger.info("🧪 开始测试优化的批量获取器")
    
    try:
        # 初始化数据库连接
        db = get_sync_db_manager()
        db.initialize()
        
        # 初始化存储类
        storage = TushareStorage(db)
        
        # 创建优化的获取器
        fetcher = OptimizedKlineFetcher(storage, max_workers=3)
        
        # 创建测试jobs
        test_jobs = [
            # 股票1: 000001.SZ
            {'code': '000001', 'market': 'SZ', 'term': 'daily', 'start_date': '20250725', 'end_date': '20250726'},
            {'code': '000001', 'market': 'SZ', 'term': 'weekly', 'start_date': '20250725', 'end_date': '20250726'},
            {'code': '000001', 'market': 'SZ', 'term': 'monthly', 'start_date': '20250725', 'end_date': '20250726'},
            
            # 股票2: 000002.SZ
            {'code': '000002', 'market': 'SZ', 'term': 'daily', 'start_date': '20250725', 'end_date': '20250726'},
            {'code': '000002', 'market': 'SZ', 'term': 'weekly', 'start_date': '20250725', 'end_date': '20250726'},
            {'code': '000002', 'market': 'SZ', 'term': 'monthly', 'start_date': '20250725', 'end_date': '20250726'},
            
            # 股票3: 000004.SZ
            {'code': '000004', 'market': 'SZ', 'term': 'daily', 'start_date': '20250725', 'end_date': '20250726'},
            {'code': '000004', 'market': 'SZ', 'term': 'weekly', 'start_date': '20250725', 'end_date': '20250726'},
            {'code': '000004', 'market': 'SZ', 'term': 'monthly', 'start_date': '20250725', 'end_date': '20250726'},
            
            # 股票4: 600000.SH
            {'code': '600000', 'market': 'SH', 'term': 'daily', 'start_date': '20250725', 'end_date': '20250726'},
            {'code': '600000', 'market': 'SH', 'term': 'weekly', 'start_date': '20250725', 'end_date': '20250726'},
            {'code': '600000', 'market': 'SH', 'term': 'monthly', 'start_date': '20250725', 'end_date': '20250726'},
            
            # 股票5: 600001.SH
            {'code': '600001', 'market': 'SH', 'term': 'daily', 'start_date': '20250725', 'end_date': '20250726'},
            {'code': '600001', 'market': 'SH', 'term': 'weekly', 'start_date': '20250725', 'end_date': '20250726'},
            {'code': '600001', 'market': 'SH', 'term': 'monthly', 'start_date': '20250725', 'end_date': '20250726'},
        ]
        
        logger.info(f"测试数据: {len(test_jobs)} 个jobs，涉及 5 只股票")
        
        # 测试分组功能
        logger.info("\n📋 测试按股票分组功能:")
        stock_groups = fetcher.group_jobs_by_stock(test_jobs)
        for stock_key, jobs in stock_groups.items():
            logger.info(f"  {stock_key}: {len(jobs)} 个jobs")
        
        # 运行优化的批量获取
        logger.info("\n🚀 开始运行优化的批量获取:")
        stats = fetcher.run_optimized_fetch(test_jobs)
        
        # 验证结果
        logger.info("\n📊 验证结果:")
        stock_kline_table = db.get_table_instance('stock_kline', 'base')
        
        for stock_key in stock_groups.keys():
            code, market = stock_key.split('.')
            count = stock_kline_table.count("code = %s AND market = %s", (code, market))
            logger.info(f"  {stock_key}: {count} 条记录")
        
        logger.info("\n✅ 优化的批量获取器测试完成")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        raise


def test_performance_comparison():
    """性能对比测试"""
    logger.info("\n⚡ 开始性能对比测试")
    
    try:
        # 初始化
        db = get_sync_db_manager()
        db.initialize()
        storage = TushareStorage(db)
        
        # 创建更多测试数据
        test_jobs = []
        for i in range(1, 11):  # 10只股票
            code = f"{i:06d}"
            market = 'SZ' if i <= 5 else 'SH'
            for term in ['daily', 'weekly', 'monthly']:
                test_jobs.append({
                    'code': code,
                    'market': market,
                    'term': term,
                    'start_date': '20250725',
                    'end_date': '20250726'
                })
        
        logger.info(f"性能测试: {len(test_jobs)} 个jobs，{len(test_jobs)//3} 只股票")
        
        # 测试不同线程数的性能
        for max_workers in [1, 3, 5]:
            logger.info(f"\n🔧 测试 {max_workers} 线程:")
            fetcher = OptimizedKlineFetcher(storage, max_workers=max_workers)
            stats = fetcher.run_optimized_fetch(test_jobs)
            
            duration = stats['end_time'] - stats['start_time']
            speed = stats['processed_jobs'] / duration if duration > 0 else 0
            logger.info(f"  耗时: {duration:.2f}秒, 速度: {speed:.2f} 任务/秒")
        
        logger.info("\n✅ 性能对比测试完成")
        
    except Exception as e:
        logger.error(f"❌ 性能测试失败: {e}")
        raise


if __name__ == "__main__":
    # 基础功能测试
    test_optimized_fetcher()
    
    # 性能对比测试
    test_performance_comparison()
    
    # 测试完成后停止数据库写入器
    from utils.db.database_writer import stop_database_writer
    stop_database_writer() 