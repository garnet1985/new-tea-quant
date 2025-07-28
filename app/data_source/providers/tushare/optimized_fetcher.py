#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from loguru import logger
from app.data_source.providers.tushare.main_storage import TushareStorage
from utils.db.database_writer import get_database_writer
from utils.performance_monitor import get_performance_monitor, PerformanceTimer


class OptimizedKlineFetcher:
    """
    优化的K线数据获取器
    支持按股票分组的批量处理和多线程并行执行
    """
    
    def __init__(self, storage: TushareStorage, max_workers=5):
        self.storage = storage
        self.max_workers = max_workers
        self.database_writer = get_database_writer()
        self.performance_monitor = get_performance_monitor()
        self.stats = {
            'total_jobs': 0,
            'processed_jobs': 0,
            'successful_stocks': 0,
            'failed_stocks': 0,
            'start_time': None,
            'end_time': None
        }
    
    def group_jobs_by_stock(self, jobs):
        """
        将jobs按股票分组
        
        Args:
            jobs: 任务列表，每个job包含 code, market, term 等信息
            
        Returns:
            dict: {stock_key: [job1, job2, job3]}
        """
        stock_groups = defaultdict(list)
        
        for job in jobs:
            stock_key = f"{job['code']}.{job['market']}"
            stock_groups[stock_key].append(job)
        
        logger.info(f"将 {len(jobs)} 个jobs分组为 {len(stock_groups)} 只股票")
        return stock_groups
    
    def process_single_stock(self, stock_key, stock_jobs):
        """
        处理单只股票的所有周期数据
        
        Args:
            stock_key: 股票标识 (如 "000001.SZ")
            stock_jobs: 该股票的所有任务列表
            
        Returns:
            dict: 处理结果
        """
        stock_code, stock_market = stock_key.split('.')
        result = {
            'stock_key': stock_key,
            'jobs_count': len(stock_jobs),
            'success': False,
            'data_count': 0,
            'error': None
        }
        
        try:
            logger.info(f"开始处理股票 {stock_key}，共 {len(stock_jobs)} 个周期")
            
            # 收集该股票的所有数据
            all_stock_data = []
            
            for job in stock_jobs:
                try:
                    # 使用性能监控记录API请求时间
                    with PerformanceTimer(
                        self.performance_monitor, 
                        'api', 
                        'request_time',
                        {'stock': stock_key, 'term': job['term']}
                    ):
                        # 模拟API调用获取数据
                        data = self.fetch_kline_data(job)
                    
                    if data is not None and not data.empty:
                        # 转换数据格式
                        converted_data = self.convert_data_for_storage(data, job)
                        all_stock_data.extend(converted_data)
                        logger.debug(f"股票 {stock_key} {job['term']} 获取到 {len(converted_data)} 条数据")
                    else:
                        logger.warning(f"股票 {stock_key} {job['term']} 未获取到数据")
                        
                except Exception as e:
                    logger.error(f"获取股票 {stock_key} {job['term']} 数据失败: {e}")
                    # 继续处理其他周期，不中断整个股票的处理
            
            # 批量存储该股票的所有数据
            if all_stock_data:
                # 使用性能监控记录数据库写入时间
                with PerformanceTimer(
                    self.performance_monitor,
                    'database',
                    'write_time',
                    {'stock': stock_key, 'records': len(all_stock_data)}
                ):
                    # 使用数据库写入队列，避免多线程直接写入
                    self.database_writer.queue_write('stock_kline', all_stock_data)
                
                result['success'] = True
                result['data_count'] = len(all_stock_data)
                logger.info(f"✅ 股票 {stock_key} 处理完成，队列 {len(all_stock_data)} 条数据")
            else:
                logger.warning(f"股票 {stock_key} 没有有效数据")
                
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"❌ 处理股票 {stock_key} 失败: {e}")
        
        return result
    
    def fetch_kline_data(self, job):
        """
        获取K线数据（模拟实现）
        
        Args:
            job: 任务信息
            
        Returns:
            pandas.DataFrame: K线数据
        """
        # TODO: 这里应该调用实际的Tushare API
        # 目前返回模拟数据用于测试
        import pandas as pd
        
        # 模拟API延迟
        time.sleep(0.1)
        
        # 生成模拟数据
        mock_data = pd.DataFrame([
            {
                'ts_code': f"{job['code']}.{job['market']}",
                'trade_date': job['start_date'],
                'open': 12.50,
                'close': 12.80,
                'high': 12.95,
                'low': 12.45,
                'change': 0.30,
                'pct_chg': 2.40,
                'pre_close': 12.50,
                'vol': 1500000,
                'amount': 19000000.00
            }
        ])
        
        return mock_data
    
    def convert_data_for_storage(self, data, job):
        """
        转换数据格式以适配存储
        
        Args:
            data: pandas DataFrame
            job: 任务信息
            
        Returns:
            list: 转换后的数据列表
        """
        if data is None or data.empty:
            return []
        
        # 将 pandas DataFrame 转换为字典列表
        if hasattr(data, 'to_dict'):
            data_list = data.to_dict('records')
        elif isinstance(data, list):
            data_list = data
        else:
            data_list = [data]
        
        # 转换数据格式
        converted_data = []
        for item in data_list:
            converted_item = {
                'code': job['code'],
                'market': job['market'],
                'term': job['term'],
                'date': item.get('trade_date', ''),
                'open': item.get('open', 0),
                'close': item.get('close', 0),
                'highest': item.get('high', 0),
                'lowest': item.get('low', 0),
                'priceChangeDelta': item.get('change', 0),
                'priceChangeRateDelta': item.get('pct_chg', 0),
                'preClose': item.get('pre_close', 0),
                'volume': item.get('vol', 0),
                'amount': item.get('amount', 0)
            }
            converted_data.append(converted_item)
        
        return converted_data
    
    def run_optimized_fetch(self, jobs):
        """
        运行优化的批量获取流程
        
        Args:
            jobs: 任务列表
            
        Returns:
            dict: 执行统计信息
        """
        self.stats['start_time'] = time.time()
        self.stats['total_jobs'] = len(jobs)
        
        logger.info(f"🚀 开始优化批量获取，共 {len(jobs)} 个任务，最大线程数: {self.max_workers}")
        
        try:
            # 1. 按股票分组
            stock_groups = self.group_jobs_by_stock(jobs)
            
            # 2. 多线程处理股票组
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有股票的处理任务
                future_to_stock = {
                    executor.submit(self.process_single_stock, stock_key, stock_jobs): stock_key
                    for stock_key, stock_jobs in stock_groups.items()
                }
                
                # 收集结果
                results = []
                for future in as_completed(future_to_stock):
                    stock_key = future_to_stock[future]
                    try:
                        result = future.result()
                        results.append(result)
                        
                        # 更新统计
                        self.stats['processed_jobs'] += result['jobs_count']
                        if result['success']:
                            self.stats['successful_stocks'] += 1
                        else:
                            self.stats['failed_stocks'] += 1
                            
                    except Exception as e:
                        logger.error(f"处理股票 {stock_key} 时发生异常: {e}")
                        self.stats['failed_stocks'] += 1
            
            # 3. 等待所有数据写入完成
            logger.info("等待数据库写入队列处理完成...")
            self.database_writer.flush()
            
            # 4. 输出统计信息
            self.stats['end_time'] = time.time()
            self.print_statistics(results)
            
            return self.stats
            
        except Exception as e:
            logger.error(f"批量获取过程中发生错误: {e}")
            raise
    
    def print_statistics(self, results):
        """打印执行统计信息"""
        duration = self.stats['end_time'] - self.stats['start_time']
        
        logger.info("📊 执行统计:")
        logger.info(f"  总耗时: {duration:.2f} 秒")
        logger.info(f"  总任务数: {self.stats['total_jobs']}")
        logger.info(f"  处理任务数: {self.stats['processed_jobs']}")
        logger.info(f"  成功股票数: {self.stats['successful_stocks']}")
        logger.info(f"  失败股票数: {self.stats['failed_stocks']}")
        logger.info(f"  平均处理速度: {self.stats['processed_jobs']/duration:.2f} 任务/秒")
        
        # 详细结果
        successful_results = [r for r in results if r['success']]
        if successful_results:
            total_data = sum(r['data_count'] for r in successful_results)
            logger.info(f"  总数据条数: {total_data}")
            logger.info(f"  平均每只股票数据条数: {total_data/len(successful_results):.1f}")
        
        # 数据库写入统计
        db_stats = self.database_writer.get_stats()
        logger.info("  数据库写入统计:")
        logger.info(f"    总写入任务: {db_stats['total_writes']}")
        logger.info(f"    批量写入次数: {db_stats['batch_writes']}")
        logger.info(f"    强制刷新次数: {db_stats['flush_writes']}")
        logger.info(f"    写入错误数: {db_stats['errors']}")
        
        # 性能监控统计
        logger.info("  性能监控统计:")
        self.performance_monitor.print_performance_summary(window_seconds=60)
        
        failed_results = [r for r in results if not r['success']]
        if failed_results:
            logger.warning(f"  失败股票: {[r['stock_key'] for r in failed_results]}") 