#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试线程安全数据库管理器
"""

import threading
import time
from loguru import logger
from utils.db.thread_safe_db_manager import get_thread_safe_db_manager, close_thread_safe_db_manager
from utils.db.thread_safe_db_model import ThreadSafeBaseTableModel
from app.data_source.providers.tushare.main import Tushare

def test_thread_safe_db_manager():
    """测试线程安全数据库管理器"""
    logger.info("🧪 测试线程安全数据库管理器")
    
    try:
        # 获取线程安全的数据库管理器
        db_manager = get_thread_safe_db_manager()
        
        # 测试基本功能
        logger.info("测试基本查询功能...")
        result = db_manager.execute_query("SELECT 1 as test")
        logger.info(f"查询结果: {result}")
        
        # 测试统计信息
        stats = db_manager.get_stats()
        logger.info(f"数据库统计: {stats}")
        
        # 测试线程安全的表模型
        logger.info("测试线程安全的表模型...")
        stock_kline_model = ThreadSafeBaseTableModel('stock_kline', 'base')
        
        # 测试查询
        count = stock_kline_model.count()
        logger.info(f"stock_kline 表记录数: {count}")
        
        # 测试大数据量写入
        logger.info("测试大数据量写入...")
        test_data = []
        for i in range(2000):  # 2000条记录，应该触发异步写入
            test_data.append({
                'code': f'TEST{i:04d}',
                'market': 'SZ',
                'term': 'daily',
                'date': '20250101',
                'open': 10.0 + i * 0.01,
                'close': 10.5 + i * 0.01,
                'highest': 11.0 + i * 0.01,
                'lowest': 9.5 + i * 0.01,
                'volume': 1000000 + i * 1000,
                'amount': 10000000 + i * 10000
            })
        
        # 使用线程安全的批量写入
        result = stock_kline_model.replace(test_data, ['code', 'market', 'term', 'date'])
        logger.info(f"批量写入结果: {result}")
        
        # 等待异步写入完成
        logger.info("等待异步写入完成...")
        stock_kline_model.wait_for_writes()
        
        # 获取最终统计
        final_stats = db_manager.get_stats()
        logger.info(f"最终统计: {final_stats}")
        
        logger.info("✅ 线程安全数据库管理器测试完成")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        raise

def test_concurrent_writes():
    """测试并发写入"""
    logger.info("🧪 测试并发写入")
    
    def worker(worker_id, data_count):
        """工作线程函数"""
        try:
            db_manager = get_thread_safe_db_manager()
            stock_kline_model = ThreadSafeBaseTableModel('stock_kline', 'base')
            
            # 生成测试数据
            test_data = []
            for i in range(data_count):
                test_data.append({
                    'code': f'WORKER{worker_id:02d}_{i:04d}',
                    'market': 'SZ',
                    'term': 'daily',
                    'date': '20250101',
                    'open': 10.0 + i * 0.01,
                    'close': 10.5 + i * 0.01,
                    'highest': 11.0 + i * 0.01,
                    'lowest': 9.5 + i * 0.01,
                    'volume': 1000000 + i * 1000,
                    'amount': 10000000 + i * 10000
                })
            
            # 执行写入
            result = stock_kline_model.replace(test_data, ['code', 'market', 'term', 'date'])
            logger.info(f"Worker {worker_id} 写入完成: {result} 条记录")
            
        except Exception as e:
            logger.error(f"Worker {worker_id} 失败: {e}")
    
    try:
        # 创建多个工作线程
        threads = []
        for i in range(5):  # 5个并发线程
            thread = threading.Thread(target=worker, args=(i, 500))  # 每个线程写入500条记录
            threads.append(thread)
        
        # 启动所有线程
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # 等待所有异步写入完成
        db_manager = get_thread_safe_db_manager()
        db_manager.wait_for_writes()
        
        # 获取统计信息
        stats = db_manager.get_stats()
        
        logger.info(f"✅ 并发写入测试完成")
        logger.info(f"总耗时: {end_time - start_time:.2f}秒")
        logger.info(f"统计信息: {stats}")
        
    except Exception as e:
        logger.error(f"并发写入测试失败: {e}")
        raise

def test_large_data_handling():
    """测试大数据量处理"""
    logger.info("🧪 测试大数据量处理")
    
    try:
        db_manager = get_thread_safe_db_manager()
        stock_kline_model = ThreadSafeBaseTableModel('stock_kline', 'base')
        
        # 生成大量测试数据
        large_data = []
        for i in range(10000):  # 10000条记录
            large_data.append({
                'code': f'LARGE{i:05d}',
                'market': 'SZ',
                'term': 'daily',
                'date': '20250101',
                'open': 10.0 + i * 0.001,
                'close': 10.5 + i * 0.001,
                'highest': 11.0 + i * 0.001,
                'lowest': 9.5 + i * 0.001,
                'volume': 1000000 + i * 100,
                'amount': 10000000 + i * 1000
            })
        
        logger.info(f"开始写入 {len(large_data)} 条记录...")
        start_time = time.time()
        
        # 执行写入
        result = stock_kline_model.replace(large_data, ['code', 'market', 'term', 'date'])
        
        # 等待异步写入完成
        stock_kline_model.wait_for_writes()
        
        end_time = time.time()
        
        # 获取统计信息
        stats = db_manager.get_stats()
        
        logger.info(f"✅ 大数据量处理测试完成")
        logger.info(f"写入结果: {result}")
        logger.info(f"总耗时: {end_time - start_time:.2f}秒")
        logger.info(f"统计信息: {stats}")
        
    except Exception as e:
        logger.error(f"大数据量处理测试失败: {e}")
        raise

if __name__ == "__main__":
    try:
        # 运行所有测试
        test_thread_safe_db_manager()
        test_concurrent_writes()
        test_large_data_handling()
        
        logger.info("🎉 所有测试完成！")
        
    except Exception as e:
        logger.error(f"测试过程中出现错误: {e}")
    finally:
        # 关闭数据库管理器
        close_thread_safe_db_manager() 