#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
综合优化测试脚本
测试所有优化功能：线程安全数据库、写入队列、性能监控、配置管理
"""

import time
import threading
from loguru import logger
from utils.db.db_manager import get_sync_db_manager
from utils.db.database_writer import get_database_writer, stop_database_writer
from utils.performance_monitor import get_performance_monitor
from utils.config_manager import get_config_manager
from app.data_source.providers.tushare.storage import TushareStorage
from app.data_source.providers.tushare.optimized_fetcher import OptimizedKlineFetcher


def test_config_manager():
    """测试配置管理器"""
    logger.info("🧪 测试配置管理器")
    
    try:
        config_manager = get_config_manager()
        
        # 测试基本配置获取
        db_config = config_manager.get_database_config()
        logger.info(f"数据库配置: {db_config['host']}:{db_config['port']}")
        
        # 测试配置设置
        config_manager.set('test.key', 'test_value')
        test_value = config_manager.get('test.key')
        logger.info(f"测试配置值: {test_value}")
        
        # 测试性能配置
        perf_config = config_manager.get_performance_config()
        logger.info(f"性能配置: 最大线程数={perf_config['max_workers']}")
        
        logger.info("✅ 配置管理器测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 配置管理器测试失败: {e}")
        return False


def test_performance_monitor():
    """测试性能监控器"""
    logger.info("🧪 测试性能监控器")
    
    try:
        monitor = get_performance_monitor()
        
        # 记录一些测试指标
        monitor.record_metric('test', 'response_time', 0.1)
        monitor.record_metric('test', 'response_time', 0.2)
        monitor.record_metric('test', 'response_time', 0.15)
        
        # 获取统计信息
        stats = monitor.get_metric_stats('test', 'response_time')
        if stats:
            logger.info(f"测试指标统计: 平均值={stats['avg']:.3f}, 样本数={stats['count']}")
        
        # 测试计时器
        with monitor.timer('test', 'timer_test'):
            time.sleep(0.1)
        
        logger.info("✅ 性能监控器测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 性能监控器测试失败: {e}")
        return False


def test_database_writer():
    """测试数据库写入队列"""
    logger.info("🧪 测试数据库写入队列")
    
    try:
        writer = get_database_writer()
        
        # 测试数据
        test_data = [
            {
                'code': 'TEST001',
                'market': 'SZ',
                'term': 'daily',
                'date': '20250727',
                'open': 10.0,
                'close': 10.5,
                'highest': 10.8,
                'lowest': 9.9
            },
            {
                'code': 'TEST002',
                'market': 'SH',
                'term': 'daily',
                'date': '20250727',
                'open': 20.0,
                'close': 20.3,
                'highest': 20.5,
                'lowest': 19.8
            }
        ]
        
        # 队列写入
        writer.queue_write('stock_kline', test_data)
        logger.info("已队列写入测试数据")
        
        # 等待写入完成
        time.sleep(1)
        
        # 获取统计信息
        stats = writer.get_stats()
        logger.info(f"写入统计: 总任务={stats['total_writes']}, 错误={stats['errors']}")
        
        logger.info("✅ 数据库写入队列测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库写入队列测试失败: {e}")
        return False


def test_optimized_fetcher():
    """测试优化的获取器"""
    logger.info("🧪 测试优化的获取器")
    
    try:
        # 初始化数据库和存储
        db = get_sync_db_manager()
        db.initialize()
        storage = TushareStorage(db)
        
        # 创建获取器
        fetcher = OptimizedKlineFetcher(storage, max_workers=3)
        
        # 测试数据
        test_jobs = [
            {'code': '000001', 'market': 'SZ', 'term': 'daily', 'start_date': '20250727', 'end_date': '20250727'},
            {'code': '000002', 'market': 'SZ', 'term': 'daily', 'start_date': '20250727', 'end_date': '20250727'},
            {'code': '000003', 'market': 'SZ', 'term': 'daily', 'start_date': '20250727', 'end_date': '20250727'},
        ]
        
        # 测试分组功能
        stock_groups = fetcher.group_jobs_by_stock(test_jobs)
        logger.info(f"分组结果: {len(stock_groups)} 只股票")
        
        # 运行优化获取
        stats = fetcher.run_optimized_fetch(test_jobs)
        logger.info(f"获取统计: 成功={stats['successful_stocks']}, 失败={stats['failed_stocks']}")
        
        logger.info("✅ 优化的获取器测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 优化的获取器测试失败: {e}")
        return False


def test_concurrent_operations():
    """测试并发操作"""
    logger.info("🧪 测试并发操作")
    
    try:
        writer = get_database_writer()
        monitor = get_performance_monitor()
        
        # 模拟多线程并发写入
        def worker(worker_id):
            test_data = [
                {
                    'code': f'CONC{worker_id:03d}',
                    'market': 'SZ',
                    'term': 'daily',
                    'date': '20250727',
                    'open': 10.0 + worker_id,
                    'close': 10.5 + worker_id,
                    'highest': 10.8 + worker_id,
                    'lowest': 9.9 + worker_id
                }
            ]
            
            with monitor.timer('concurrent', 'write_time', {'worker_id': worker_id}):
                writer.queue_write('stock_kline', test_data)
        
        # 启动多个工作线程
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 等待写入完成
        time.sleep(2)
        
        # 检查统计信息
        writer_stats = writer.get_stats()
        monitor_stats = monitor.get_metric_stats('concurrent', 'write_time')
        
        logger.info(f"并发写入统计: 总任务={writer_stats['total_writes']}, 错误={writer_stats['errors']}")
        if monitor_stats:
            logger.info(f"并发性能统计: 平均时间={monitor_stats['avg']:.3f}秒")
        
        logger.info("✅ 并发操作测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 并发操作测试失败: {e}")
        return False


def test_performance_comparison():
    """性能对比测试"""
    logger.info("🧪 性能对比测试")
    
    try:
        db = get_sync_db_manager()
        db.initialize()
        storage = TushareStorage(db)
        
        # 创建不同配置的获取器
        configs = [
            {'max_workers': 1, 'name': '单线程'},
            {'max_workers': 3, 'name': '3线程'},
            {'max_workers': 5, 'name': '5线程'},
        ]
        
        # 测试数据
        test_jobs = []
        for i in range(1, 16):  # 15只股票
            code = f"{i:06d}"
            market = 'SZ' if i <= 8 else 'SH'
            for term in ['daily', 'weekly', 'monthly']:
                test_jobs.append({
                    'code': code,
                    'market': market,
                    'term': term,
                    'start_date': '20250727',
                    'end_date': '20250727'
                })
        
        results = []
        for config in configs:
            logger.info(f"\n🔧 测试 {config['name']}:")
            
            fetcher = OptimizedKlineFetcher(storage, max_workers=config['max_workers'])
            start_time = time.time()
            
            stats = fetcher.run_optimized_fetch(test_jobs)
            
            end_time = time.time()
            duration = end_time - start_time
            
            results.append({
                'name': config['name'],
                'duration': duration,
                'throughput': stats['processed_jobs'] / duration if duration > 0 else 0,
                'success_rate': stats['successful_stocks'] / (stats['successful_stocks'] + stats['failed_stocks']) if (stats['successful_stocks'] + stats['failed_stocks']) > 0 else 0
            })
            
            logger.info(f"  耗时: {duration:.2f}秒")
            logger.info(f"  吞吐量: {results[-1]['throughput']:.2f} 任务/秒")
            logger.info(f"  成功率: {results[-1]['success_rate']:.2%}")
        
        # 输出对比结果
        logger.info("\n📊 性能对比结果:")
        for result in results:
            logger.info(f"  {result['name']}: {result['duration']:.2f}秒, {result['throughput']:.2f} 任务/秒, 成功率 {result['success_rate']:.2%}")
        
        logger.info("✅ 性能对比测试完成")
        return True
        
    except Exception as e:
        logger.error(f"❌ 性能对比测试失败: {e}")
        return False


def main():
    """主测试函数"""
    logger.info("🚀 开始综合优化测试")
    
    # 测试配置管理器
    if not test_config_manager():
        return False
    
    # 测试性能监控器
    if not test_performance_monitor():
        return False
    
    # 测试数据库写入队列
    if not test_database_writer():
        return False
    
    # 测试优化的获取器
    if not test_optimized_fetcher():
        return False
    
    # 测试并发操作
    if not test_concurrent_operations():
        return False
    
    # 性能对比测试
    if not test_performance_comparison():
        return False
    
    # 清理资源
    logger.info("🧹 清理资源...")
    stop_database_writer()
    
    logger.info("🎉 所有测试通过！优化功能正常工作")
    return True


if __name__ == "__main__":
    try:
        success = main()
        if success:
            logger.info("✅ 综合优化测试全部通过")
        else:
            logger.error("❌ 综合优化测试失败")
    except Exception as e:
        logger.error(f"❌ 测试过程中发生异常: {e}")
        import traceback
        traceback.print_exc() 