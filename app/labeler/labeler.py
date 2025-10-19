#!/usr/bin/env python3
"""
股票标签算法服务

位置：app/labeler/（与analyzer、data_loader、data_source并列）

职责：
- 股票标签的计算算法
- 标签分类和定义管理
- 批量标签计算和更新
- 标签质量评估和优化

架构：
- LabelerService: 主服务入口
- BaseLabelCalculator: 标签计算器基类
- 具体计算器: 各种标签的具体计算实现
- LabelMapping: 标签映射定义
"""

from datetime import timedelta
import time
from typing import Dict, List, Any, Optional, Tuple
from utils.date.date_utils import DateUtils
import pandas as pd
from loguru import logger
from utils.progress.progress_tracker import ProgressTrackerManager
from utils.worker import FuturesWorker, ThreadExecutionMode
from .base_calculator import BaseLabelCalculator, LabelCalculatorRegistry
from .conf.config import LabelConfig
from .calculators import (
    MarketCapLabelCalculator,
    IndustryLabelCalculator, 
    VolatilityLabelCalculator,
    VolumeLabelCalculator,
    FinancialLabelCalculator
)
from .conf.label_mapping import LabelMapping
from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader


class LabelerService:
    """
    股票标签算法服务
    
    提供股票标签的计算、管理和查询功能
    """
    
    def __init__(self, db: Optional[DatabaseManager] = None):
        """
        初始化标签服务
        
        Args:
            db: 数据库管理器实例，如果为None则创建新实例
        """
        if db is None:
            db = DatabaseManager()
            db.initialize()
        
        self.db = db
        self.data_loader = DataLoader(self.db)
        
        # 初始化标签定义管理器
        self.label_definitions = LabelMapping()
        
        # 初始化计算器注册表
        self.registry = LabelCalculatorRegistry()
        self._register_calculators()
        
        # 缓存计算器实例
        self._calculator_instances = {}
        
    
    def _register_calculators(self):
        """注册所有标签计算器"""
        self.registry.register_calculator(MarketCapLabelCalculator, 'market_cap')
        self.registry.register_calculator(IndustryLabelCalculator, 'industry')
        self.registry.register_calculator(VolatilityLabelCalculator, 'volatility')
        self.registry.register_calculator(VolumeLabelCalculator, 'volume')
        self.registry.register_calculator(FinancialLabelCalculator, 'financial')
        
        logger.info(f"✅ 已注册 {len(self.registry.calculators)} 个标签计算器")
    
    def get_calculator(self, category: str) -> Optional[BaseLabelCalculator]:
        """
        获取指定分类的计算器实例
        
        Args:
            category: 标签分类
            
        Returns:
            BaseLabelCalculator: 计算器实例
        """
        if category not in self._calculator_instances:
            calculator_class = self.registry.get_calculator(category, self.data_loader, self.label_definitions)
            if calculator_class:
                self._calculator_instances[category] = calculator_class
            else:
                logger.warning(f"未找到标签分类 {category} 的计算器")
                return None
        
        return self._calculator_instances.get(category)
    
    # ============ 标签数据更新接口 ============
    
    def renew(self, last_market_open_day: str, is_refresh: bool = False):
        """
        标签数据增量更新
        
        Args:
            last_market_open_day: 最新交易日
            is_refresh: 是否刷新所有股票标签（重新计算所有标签，用于添加新计算器等场景）
        """
        logger.info(f"🔄 开始标签数据更新: {last_market_open_day}, 刷新模式: {is_refresh}")

        start_time = time.time()
        
        try:
            # 1. 获取股票列表和标签更新情况
            stocks_to_process = self._get_stocks_and_update_status(last_market_open_day, is_refresh)
            if not stocks_to_process:
                logger.info("📋 没有需要更新的股票")
                return
            
            logger.info(f"📋 找到 {len(stocks_to_process)} 只需要更新的股票")
            
            # 2. 生成job任务
            update_jobs = self._generate_jobs(stocks_to_process, last_market_open_day)
            if not update_jobs:
                logger.info("📋 没有需要执行的job任务")
                return
            
            logger.info(f"📋 生成了 {len(update_jobs)} 个job任务")
            
            # 3. 执行job任务（单线程或多线程）
            self._execute_jobs(update_jobs)
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ 标签数据更新完成: {last_market_open_day}, 耗时 {elapsed_time:.2f} 秒")
            
        except Exception as e:
            logger.error(f"❌ 标签数据更新失败: {e}")
            raise e
    
    def _get_stocks_and_update_status(self, last_market_open_day: str, is_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        获取股票列表和标签更新情况
        
        Args:
            last_market_open_day: 最新交易日
            is_refresh: 是否刷新所有股票标签
            
        Returns:
            List[Dict]: 需要更新的股票列表
        """
        # 获取所有股票列表（过滤ST、科创板等）
        all_stocks = self.data_loader.load_stock_list(filtered=True)
        logger.info(f"📋 获取到 {len(all_stocks)} 只股票")
        
        if is_refresh:
            logger.info(f"🔄 刷新模式：重新计算 {len(all_stocks)}只股票的所有标签")
            return all_stocks
        
        # 增量更新模式：批量获取所有股票的最后更新时间
        stock_ids = [stock['id'] for stock in all_stocks]
        stock_last_update_dates = self.data_loader.label_loader.get_all_stocks_last_update_dates(stock_ids)
        
        stocks_needing_update = []
        current_dt = DateUtils.parse_yyyymmdd(last_market_open_day)
        
        for stock in all_stocks:
            stock_id = stock['id']
            last_update_date = stock_last_update_dates.get(stock_id)
            
            if last_update_date is None:
                # 从未更新过，需要更新
                stocks_needing_update.append(stock)
                continue
            
            # 计算距离上次更新的天数
            last_update_dt = DateUtils.parse_yyyymmdd(last_update_date)
            days_since_update = (current_dt - last_update_dt).days
            
            if LabelConfig.should_update_stock(days_since_update):
                stocks_needing_update.append(stock)
        
        return stocks_needing_update
    
    def _generate_jobs(self, stocks_to_process: List[Dict[str, Any]], last_market_open_day: str) -> List[Dict[str, Any]]:
        """
        生成job任务列表
        
        Args:
            stocks_to_process: 需要处理的股票列表
            last_market_open_day: 最新交易日
            
        Returns:
            List[Dict]: job任务列表
        """
        # 获取需要计算的标签分类
        categories_to_calculate = []
        for category in LabelMapping.get_categories().keys():
            if not LabelConfig.is_static_category(category):
                categories_to_calculate.append(category)
        
        jobs = []
        for stock in stocks_to_process:
            jobs.append({
                'id': stock['id'],  # 添加id字段
                'data': {
                    'stock': stock,
                    'target_date': last_market_open_day,
                    'categories': categories_to_calculate
                }
            })
        
        return jobs
    
    def _execute_jobs(self, jobs: List[Dict[str, Any]]):
        """
        执行job任务（单线程或多线程）
        
        Args:
            jobs: job任务列表
        """
        if not jobs:
            logger.info("📋 没有任务需要执行")
            return
        
        logger.info(f"🔄 开始执行job任务: {len(jobs)}个任务")
        
        # 获取性能配置
        performance_config = LabelConfig.get_performance_config()
        multithread_threshold = performance_config.get('multithread_threshold', 50)
        
        if len(jobs) >= multithread_threshold:
            logger.info(f"🚀 使用多线程执行: {len(jobs)}个任务 (阈值: {multithread_threshold})")
            self._execute_jobs_multithreaded(jobs)
        else:
            logger.info(f"🔄 使用单线程执行: {len(jobs)}个任务 (阈值: {multithread_threshold})")
            self._execute_jobs_singlethreaded(jobs)
    
    def _generate_update_jobs(self, last_market_open_day: str, is_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        生成更新任务列表
        
        Args:
            last_market_open_day: 最新交易日
            is_refresh: 是否刷新所有股票标签
            
        Returns:
            List[Dict]: 任务列表
        """
        jobs = []
        
        # 获取所有股票列表（使用过滤规则，排除ST、科创板等）
        all_stocks = self.data_loader.load_stock_list(filtered=True)
        
        # 获取需要计算的标签分类
        categories_to_calculate = []
        for category in LabelMapping.get_categories().keys():
            if not LabelConfig.is_static_category(category):
                categories_to_calculate.append(category)
        
        if is_refresh:
            logger.info(f"🔄 刷新模式：重新计算 {len(all_stocks)}只股票的所有标签")
            stocks_to_process = all_stocks
        else:
            # 增量更新模式：批量获取所有股票的最后更新时间
            stocks_needing_update = self._get_stocks_needing_update_batch(all_stocks, last_market_open_day)
            
            if stocks_needing_update:
                logger.info(f"📋 增量更新模式：{len(stocks_needing_update)}只股票需要更新")
                stocks_to_process = stocks_needing_update
            else:
                logger.info("📋 没有股票需要更新")
                return []
        
        # 生成任务
        for stock in stocks_to_process:
            jobs.append({
                'id': stock['id'],  # FuturesWorker期望的字段名
                'data': {
                    'stock': stock,  # 完整的股票信息
                    'target_date': last_market_open_day,
                    'categories': categories_to_calculate
                }
            })
        
        return jobs
    
    def _get_stocks_needing_update_batch(self, all_stocks: List[Dict], last_market_open_day: str) -> List[Dict]:
        """
        批量获取需要更新的股票列表
        
        Args:
            all_stocks: 所有股票对象列表
            last_market_open_day: 最新交易日
            
        Returns:
            List[Dict]: 需要更新的股票对象列表
        """
        try:
            # 提取股票ID列表
            stock_ids = [stock['id'] for stock in all_stocks]
            
            # 一次性获取所有股票的最后更新时间
            stock_last_update_dates = self.data_loader.label_loader.get_all_stocks_last_update_dates(stock_ids)
            
            stocks_needing_update = []
            current_dt = DateUtils.parse_yyyymmdd(last_market_open_day)
            
            for stock in all_stocks:
                stock_id = stock['id']
                last_update_date = stock_last_update_dates.get(stock_id)
                
                if last_update_date is None:
                    # 从未更新过，需要更新
                    stocks_needing_update.append(stock)
                    continue
                
                # 计算距离上次更新的天数
                last_update_dt = DateUtils.parse_yyyymmdd(last_update_date)
                days_since_update = (current_dt - last_update_dt).days
                
                
                if LabelConfig.should_update_stock(days_since_update):
                    stocks_needing_update.append(stock)
            
            return stocks_needing_update
            
        except Exception as e:
            logger.error(f"批量获取需要更新的股票失败: {e}")
            return []
    
    
    def _execute_update_jobs(self, jobs: List[Dict[str, Any]], target_date: str):
        """
        执行更新任务列表
        
        Args:
            jobs: 任务列表
            target_date: 目标日期
        """
        if not jobs:
            logger.info("📋 没有任务需要执行")
            return
        
        logger.info(f"🔄 开始执行标签更新任务: {len(jobs)}个任务")
        
        # 获取性能配置
        performance_config = LabelConfig.get_performance_config()
        multithread_threshold = performance_config.get('multithread_threshold', 50)
        
        if len(jobs) >= multithread_threshold:
            logger.info(f"🚀 使用多线程执行: {len(jobs)}个任务 (阈值: {multithread_threshold})")
            self._execute_jobs_multithreaded(jobs)
        else:
            logger.info(f"🔄 使用单线程执行: {len(jobs)}个任务 (阈值: {multithread_threshold})")
            self._execute_jobs_singlethreaded(jobs)
    
    def _execute_jobs_singlethreaded(self, jobs: List[Dict[str, Any]]):
        """
        单线程执行任务
        
        Args:
            jobs: 任务列表
        """
        success_count = 0
        failed_count = 0
        total_jobs = len(jobs)
        
        for i, job in enumerate(jobs, 1):
            try:
                result = self._calculate_single_stock_labels_wrapper(job['data'])
                if result['status'] == 'success':
                    success_count += 1
                    stock_info = job['data']['stock']
                    stock_id = stock_info['id']
                    stock_name = stock_info.get('name', stock_id)
                    labels_count = result['result'].get('dates_count', 0)
                    progress = int(i * 100 / total_jobs)
                    
                    if labels_count > 0:
                        logger.info(f"股票 {stock_id} ({stock_name}) 计算完毕，更新{labels_count}个标签 总进度 {progress}%")
                    else:
                        total_dates = result['result'].get('total_dates', 0)
                        if total_dates > 0:
                            logger.warning(f"股票 {stock_id} ({stock_name}) 尝试计算标签但未生成任何标签 总进度 {progress}%")
                        else:
                            logger.info(f"股票 {stock_id} ({stock_name}) 不需要标签计算 总进度 {progress}%")
                else:
                    failed_count += 1
                    stock_info = job['data']['stock']
                    stock_id = stock_info['id']
                    stock_name = stock_info.get('name', stock_id)
                    progress = int(i * 100 / total_jobs)
                    logger.info(f"股票 {stock_id} ({stock_name}) 标签计算失败 总进度 {progress}%")
            except Exception as e:
                failed_count += 1
                stock_info = job['data']['stock']
                stock_id = stock_info['id']
                stock_name = stock_info.get('name', stock_id)
                progress = int(i * 100 / total_jobs)
                logger.info(f"股票 {stock_id} ({stock_name}) 任务执行失败 总进度 {progress}%")
        
        logger.info(f"✅ 单线程执行完成: 成功 {success_count}, 失败 {failed_count}")
    
    def _execute_jobs_multithreaded(self, jobs: List[Dict[str, Any]]):
        """
        多线程执行任务
        
        Args:
            jobs: 任务列表
        """
        performance_config = LabelConfig.get_performance_config()
        max_workers = performance_config.get('max_workers', 10)
        max_threads_limit = performance_config.get('max_threads_limit', 20)
        
        # 限制最大线程数
        max_workers = min(max_workers, len(jobs), max_threads_limit)
        
        logger.info(f"🚀 启动多线程执行: {len(jobs)}个任务, {max_workers}个线程")
        
        # 初始化进度计数器
        self._completed_count = 0
        self._total_jobs = len(jobs)
        
        # 创建多线程工作器
        worker = FuturesWorker(
            max_workers=max_workers,
            execution_mode=ThreadExecutionMode.PARALLEL,
            job_executor=self._calculate_single_stock_labels_wrapper_with_progress,
            enable_monitoring=False,
            timeout=1200.0,  # 20分钟超时
            is_verbose=False
        )
        
        # 执行任务
        stats = worker.run_jobs(jobs)
        worker.print_stats()
        
        logger.info(f"✅ 多线程执行完成: 成功 {stats.get('success_count', 0)}, 失败 {stats.get('failed_count', 0)}")
    
    def _calculate_single_stock_labels_wrapper_with_progress(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        带进度显示的标签计算包装器（多线程模式）
        
        Args:
            job_data: 任务数据
            
        Returns:
            Dict: 执行结果
        """
        stock_info = job_data['stock']
        stock_id = stock_info['id']
        stock_name = stock_info.get('name', stock_id)
        target_date = job_data['target_date']
        categories = job_data['categories']
        
        try:
            result = self._calculate_single_stock_labels(stock_id, target_date, categories)
            labels_count = result.get('dates_count', 0)
            
            # 更新进度计数器
            self._completed_count += 1
            progress = int(self._completed_count * 100 / self._total_jobs)
            
            if labels_count > 0:
                logger.info(f"股票 {stock_id} ({stock_name}) 计算完毕，更新{labels_count}个标签 总进度 {progress}%")
            else:
                total_dates = result.get('total_dates', 0)
                if total_dates > 0:
                    logger.warning(f"股票 {stock_id} ({stock_name}) 尝试计算标签但未生成任何标签 总进度 {progress}%")
                else:
                    logger.info(f"股票 {stock_id} ({stock_name}) 不需要标签计算 总进度 {progress}%")
            
            return {
                'job_id': stock_id,
                'status': 'success',
                'result': result
            }
        except Exception as e:
            # 更新进度计数器（即使失败也要计数）
            self._completed_count += 1
            progress = int(self._completed_count * 100 / self._total_jobs)
            
            logger.info(f"股票 {stock_id} ({stock_name}) 标签计算失败 总进度 {progress}%")
            logger.error(f"❌ 股票 {stock_id} 标签计算失败: {e}")
            return {
                'job_id': stock_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _calculate_single_stock_labels_wrapper(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        单股票标签计算包装器（适配FuturesWorker）
        
        Args:
            job_data: 任务数据
            
        Returns:
            Dict: 执行结果
        """
        stock_info = job_data['stock']
        stock_id = stock_info['id']
        target_date = job_data['target_date']
        categories = job_data['categories']
        
        try:
            result = self._calculate_single_stock_labels(stock_id, target_date, categories)
            return {
                'job_id': stock_id,
                'status': 'success',
                'result': result
            }
        except Exception as e:
            logger.error(f"❌ 股票 {stock_id} 标签计算失败: {e}")
            return {
                'job_id': stock_id,
                'status': 'failed',
                'error': str(e)
            }
    
    def _calculate_single_stock_labels(self, stock_id: str, target_date: str, categories: List[str]) -> Dict[str, Any]:
        """
        计算单只股票的所有标签 - 使用新的循环推进算法
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期（最新交易日）
            categories: 需要计算的标签分类
            
        Returns:
            Dict: 计算结果
        """
        try:
            # 1. 获取所有K线数据
            klines_dict = self._get_all_stock_klines_data(stock_id)
            if not klines_dict:
                logger.warning(f"股票 {stock_id} 没有K线数据，跳过")
                return {'success': True, 'labels_saved': 0, 'dates_count': 0, 'total_dates': 0}
            
            # 2. 执行循环推进算法
            total_labels_saved = self._execute_loop_algorithm(stock_id, target_date, categories, klines_dict)
            
            return {
                'stock_id': stock_id,
                'dates_count': total_labels_saved,
                'total_dates': total_labels_saved,  # 循环推进算法中，dates_count就是total_dates
                'categories': categories
            }
            
        except Exception as e:
            logger.error(f"❌ 股票 {stock_id} 标签计算异常: {e}")
            raise e
    
    def _get_all_stock_klines_data(self, stock_id: str, start_date: str = None) -> Dict[str, Dict]:
        """
        获取股票的K线数据（按日期索引）
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（可选，如果不提供则从最后更新日期开始）
            
        Returns:
            Dict[str, Dict]: 按日期索引的K线数据字典
        """
        try:
            # 如果没有提供开始日期，则从最后更新日期开始
            if not start_date:
                stock_last_update_dates = self.data_loader.label_loader.get_all_stocks_last_update_dates([stock_id])
                last_update_date = stock_last_update_dates.get(stock_id)
                
                if last_update_date:
                    # 从最后更新日期开始加载
                    start_date = last_update_date
                else:
                    # 如果没有更新记录，只加载最近3年的数据
                    from utils.date.date_utils import DateUtils
                    current_date = DateUtils.get_current_date_str()
                    start_date = DateUtils.get_date_after_days(current_date, -3*365)  # 3年前
            
            # 获取股票的K线数据
            from utils.date.date_utils import DateUtils
            current_date = DateUtils.get_current_date_str()
            klines = self.data_loader.load_klines(stock_id, start_date=start_date, end_date=current_date)
            if not klines:
                return {}
            
            # 转换为按日期索引的字典
            klines_dict = {kline['date']: kline for kline in klines}
            return klines_dict
        except Exception as e:
            logger.error(f"获取股票 {stock_id} K线数据失败: {e}")
            return {}
    
    def _get_stock_klines_data_for_testing(self, stock_id: str, start_date: str, end_date: str) -> Dict[str, Dict]:
        """
        获取指定日期范围的K线数据（用于测试）
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict[str, Dict]: 按日期索引的K线数据字典
        """
        try:
            # 获取指定日期范围的K线数据
            klines = self.data_loader.load_klines(stock_id, start_date=start_date, end_date=end_date)
            if not klines:
                return {}
            
            # 转换为按日期索引的字典
            klines_dict = {kline['date']: kline for kline in klines}
            return klines_dict
        except Exception as e:
            logger.error(f"获取股票 {stock_id} K线数据失败: {e}")
            return {}
    
    def _execute_loop_algorithm(self, stock_id: str, target_date: str, categories: List[str], klines_dict: Dict[str, Dict]) -> int:
        """
        执行循环推进算法
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期（最新交易日）
            categories: 需要计算的标签分类
            klines_dict: 按日期索引的K线数据字典
            
        Returns:
            int: 保存的标签数量
        """
        # 获取最后标签更新日期
        stock_last_update_dates = self.data_loader.label_loader.get_all_stocks_last_update_dates([stock_id])
        last_update_date = stock_last_update_dates.get(stock_id)
        
        if not last_update_date:
            # 从未更新过，从最早日期开始
            if klines_dict:
                first_kline_date = min(klines_dict.keys())
                current_date = DateUtils.parse_yyyymmdd(first_kline_date)
            else:
                return 0
        else:
            current_date = DateUtils.parse_yyyymmdd(last_update_date)
        
        MIN_INTERVAL = 15  # hard code最小间隔阈值（天）
        target_dt = DateUtils.parse_yyyymmdd(target_date)
        total_labels_saved = 0
        
        # 获取排序后的K线日期列表
        kline_dates = sorted(klines_dict.keys())
        
        # 使用二分查找优化性能
        def find_nearest_trading_day(target_date: str) -> str:
            """使用二分查找找到最近的交易日"""
            if target_date in klines_dict:
                return target_date
            
            # 二分查找最后一个小于等于target_date的日期
            left, right = 0, len(kline_dates) - 1
            result = None
            
            while left <= right:
                mid = (left + right) // 2
                if kline_dates[mid] <= target_date:
                    result = kline_dates[mid]
                    left = mid + 1
                else:
                    right = mid - 1
            
            return result
        
        # 批量保存标签数据
        labels_to_save = []
        
        while True:
            # 计算目标日期
            next_target_date = DateUtils.get_date_after_days(DateUtils.format_to_yyyymmdd(current_date), 30)
            next_target_dt = DateUtils.parse_yyyymmdd(next_target_date)
            
            # 检查是否超过结束条件
            if next_target_dt > target_dt:
                break
            
            # 查找实际交易日（使用二分查找优化）
            actual_trading_day = find_nearest_trading_day(next_target_date)
            
            if not actual_trading_day:
                # 没有找到交易日，跳过
                current_date = next_target_dt
                continue
            
            # 阈值判断
            actual_dt = DateUtils.parse_yyyymmdd(actual_trading_day)
            days_since_last_update = (actual_dt - current_date).days
            
            if days_since_last_update < MIN_INTERVAL:
                # 距离太近，跳过本次计算，强制推进到下一个30天周期
                current_date = next_target_dt
                continue
            
            # 计算标签
            labels = self._calculate_labels_for_date(stock_id, actual_trading_day, categories, klines_dict)
            if labels:
                labels_to_save.append({
                    'stock_id': stock_id,
                    'label_date': actual_trading_day,
                    'labels': labels
                })
                total_labels_saved += 1
            
            # 推进到下一个周期
            current_date = actual_dt
        
        # 批量保存所有标签
        if labels_to_save:
            self._batch_save_stock_labels(labels_to_save)
        
        return total_labels_saved
    
    def _calculate_labels_for_date(self, stock_id: str, date: str, categories: List[str], klines_dict: Dict[str, Dict]) -> List[str]:
        """
        为指定日期计算标签
        
        Args:
            stock_id: 股票代码
            date: 日期
            categories: 标签分类列表
            klines_dict: 按日期索引的K线数据字典
            
        Returns:
            List[str]: 计算出的标签列表
        """
        all_labels = []
        
        # 获取指定日期的K线数据
        target_kline = klines_dict.get(date)
        if not target_kline:
            logger.warning(f"无法找到 {stock_id} 在 {date} 的K线数据")
            return all_labels
        
        # 为标签计算器提供该日期的K线数据
        klines_for_date = [target_kline]
        
        for category in categories:
            try:
                calculator = self.get_calculator(category)
                if calculator:
                    labels = calculator.calculate_labels_for_stock(
                        stock_id, date, 
                        klines_data=klines_for_date,
                        data_loader=self.data_loader
                    )
                    if labels:
                        all_labels.extend(labels)
            except Exception as e:
                logger.warning(f"计算标签失败 {stock_id} {date} {category}: {e}")
                continue
        
        return all_labels
    
    def _generate_historical_dates(self, stock_id: str, target_date: str) -> List[str]:
        """
        生成需要计算标签的历史日期列表
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            
        Returns:
            List[str]: 日期列表
        """
        try:
            from datetime import datetime, timedelta
            
            # 获取股票的最后标签更新日期
            stock_last_update_dates = self.data_loader.label_loader.get_all_stocks_last_update_dates([stock_id])
            last_update_date = stock_last_update_dates.get(stock_id)
            
            if not last_update_date:
                # 从未更新过，从最早日期开始生成所有历史日期
                return self._generate_all_historical_dates(stock_id, target_date)
            
            # 注意：这里不应该再次检查是否需要更新
            # 因为job已经被构建，说明确实需要更新
            # 如果再次检查，可能会导致状态不一致
            
            # 增量更新策略：从最后更新日期开始，生成需要更新的日期
            # 对于长时间未更新的股票，我们需要生成更多的日期
            current_dt = DateUtils.parse_yyyymmdd(target_date)
            last_update_dt = DateUtils.parse_yyyymmdd(last_update_date)
            days_since_update = (current_dt - last_update_dt).days
            
            if days_since_update > 365:  # 超过1年未更新
                # 对于长时间未更新的股票，生成最近30天的交易日
                start_dt = DateUtils.get_date_before_days(target_date, 30)
                end_date = target_date
                klines = self.data_loader.load_klines(stock_id, start_date=start_dt, end_date=end_date)
                if klines:
                    # 返回最近的交易日
                    trading_days = [kline['date'] for kline in klines if kline.get('date')]
                    if trading_days:
                        return [trading_days[-1]]  # 返回最后一个交易日
            else:
                # 对于短期未更新的股票，使用原来的策略
                next_update_dt = DateUtils.get_date_after_days(last_update_date, 30)
                nearest_trading_day = self._find_nearest_trading_day(stock_id, next_update_dt)
                if nearest_trading_day:
                    return [nearest_trading_day]
            
            return []
            
        except Exception as e:
            logger.error(f"生成历史日期失败 {stock_id}: {e}")
            return [target_date]
    
    def _generate_all_historical_dates(self, stock_id: str, target_date: str) -> List[str]:
        """
        情况1：股票从未更新过标签，生成所有历史日期
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            
        Returns:
            List[str]: 所有历史日期列表
        """
        try:
            from datetime import datetime, timedelta
            
            # 获取股票的最早K线日期作为起始日期
            earliest_date = self._get_stock_earliest_date_from_klines(stock_id)
            if not earliest_date:
                logger.warning(f"无法获取股票 {stock_id} 的最早K线日期")
                return [target_date]
            
            start_dt = DateUtils.parse_yyyymmdd(earliest_date)
            end_dt = DateUtils.parse_yyyymmdd(target_date)
            
            dates = []
            current_dt = start_dt
            
            # 从最早日期开始，每30天生成一个标签
            while current_dt <= end_dt:
                dates.append(DateUtils.format_to_yyyymmdd(current_dt))
                current_dt = DateUtils.parse_yyyymmdd(DateUtils.get_date_after_days(DateUtils.format_to_yyyymmdd(current_dt), 30))  # 每1个月
            
            return dates
            
        except Exception as e:
            logger.error(f"生成所有历史日期失败 {stock_id}: {e}")
            return [target_date]
    
    
    def _generate_incremental_dates(self, last_update_date: str, target_date: str) -> List[str]:
        """
        情况2：股票有过标签记录，生成增量日期
        
        Args:
            last_update_date: 上次更新日期
            target_date: 目标日期
            
        Returns:
            List[str]: 增量日期列表
        """
        try:
            from datetime import datetime, timedelta
            
            start_dt = DateUtils.parse_yyyymmdd(last_update_date)
            end_dt = DateUtils.parse_yyyymmdd(target_date)
            
            dates = []
            current_dt = start_dt + timedelta(days=30)  # 从上次更新后30天开始
            
            # 从上次更新日期开始，每30天生成一个标签，直到目标日期
            while current_dt <= end_dt:
                dates.append(DateUtils.format_to_yyyymmdd(current_dt))
                current_dt = DateUtils.parse_yyyymmdd(DateUtils.get_date_after_days(DateUtils.format_to_yyyymmdd(current_dt), 30))  # 每1个月
            
            # 如果没有生成任何日期，说明距离上次更新刚好30天，直接使用目标日期
            if not dates:
                dates.append(target_date)
            
            logger.debug(f"需要计算增量标签：{len(dates)} 个日期")
            return dates
            
        except Exception as e:
            logger.error(f"生成增量日期失败: {e}")
            return [target_date]
    
    def _get_stock_earliest_date_from_klines(self, stock_id: str) -> Optional[str]:
        """
        从K线数据中获取股票的最早日期
        
        Args:
            stock_id: 股票代码
            
        Returns:
            str: 最早日期，格式为YYYYMMDD
        """
        try:
            # 获取股票的所有K线数据，取第一个日期
            all_klines = self.data_loader.load_klines(stock_id)
            
            if not all_klines:
                return None
            
            # 按日期排序，取最早的日期
            sorted_klines = sorted(all_klines, key=lambda x: x.get('date', ''))
            earliest_date = sorted_klines[0].get('date', '')
            
            if earliest_date:
                # 转换为YYYYMMDD格式
                if isinstance(earliest_date, str):
                    return earliest_date.replace('-', '')
                else:
                    return DateUtils.format_to_yyyymmdd(earliest_date)
            
            return None
            
        except Exception as e:
            logger.error(f"从K线数据获取最早日期失败 {stock_id}: {e}")
            return None
    
    
    def _get_stock_klines_data_optimized(self, stock_id: str, dates: List[str], target_date: str) -> Dict[str, List[Dict]]:
        """
        智能获取股票的K线数据（根据情况优化IO）
        
        Args:
            stock_id: 股票代码
            dates: 日期列表
            target_date: 目标日期
            
        Returns:
            Dict[str, List[Dict]]: 按日期分组的K线数据
        """
        try:
            if not dates:
                return {}
            
            # 获取股票的最后标签更新日期
            stock_last_update_dates = self.data_loader.label_loader.get_all_stocks_last_update_dates([stock_id])
            last_update_date = stock_last_update_dates.get(stock_id)
            
            if not last_update_date:
                # 情况1：股票从未更新过标签，需要获取所有历史K线数据
                return self._get_all_historical_klines_data(stock_id, dates)
            else:
                # 情况2：股票有过标签记录，只获取增量K线数据
                return self._get_incremental_klines_data(stock_id, dates, last_update_date, target_date)
            
        except Exception as e:
            logger.error(f"智能获取股票K线数据失败 {stock_id}: {e}")
            return {}
    
    def _get_all_historical_klines_data(self, stock_id: str, dates: List[str]) -> Dict[str, List[Dict]]:
        """
        情况1：获取所有历史K线数据（股票从未更新过标签）
        
        Args:
            stock_id: 股票代码
            dates: 日期列表
            
        Returns:
            Dict[str, List[Dict]]: 按日期分组的K线数据
        """
        try:
            if not dates:
                return {}
            
            # 计算日期范围，为了满足计算器需求，需要获取更长的历史数据
            from datetime import datetime, timedelta
            end_date = max(dates)
            end_dt = DateUtils.parse_yyyymmdd(end_date)
            
            # 获取足够长的历史数据（比如过去1年的数据，确保计算器有足够的历史数据）
            start_date = DateUtils.get_date_before_days(end_date, 365)
            
            # 一次性获取日期范围内的所有K线数据
            all_klines = self.data_loader.load_klines(stock_id, start_date=start_date, end_date=end_date)
            
            # 按日期分组，并为每个目标日期找到最近的交易日数据
            klines_by_date = {}
            available_dates = [kline.get('date', '') for kline in all_klines]
            
            for target_date in dates:
                # 如果目标日期本身有数据，直接使用
                if target_date in available_dates:
                    klines_by_date[target_date] = [kline for kline in all_klines if kline.get('date') == target_date]
                else:
                    # 查找最近的交易日
                    nearest_date = self._find_nearest_available_date(target_date, available_dates)
                    if nearest_date:
                        klines_by_date[target_date] = [kline for kline in all_klines if kline.get('date') == nearest_date]
                    else:
                        klines_by_date[target_date] = []
            
            return klines_by_date
            
        except Exception as e:
            logger.error(f"获取所有历史K线数据失败 {stock_id}: {e}")
            return {}
    
    def _find_nearest_available_date(self, target_date: str, available_dates: List[str]) -> Optional[str]:
        """
        在可用日期列表中找到最接近目标日期的日期
        
        Args:
            target_date: 目标日期
            available_dates: 可用日期列表
            
        Returns:
            Optional[str]: 最接近的日期，如果找不到返回None
        """
        try:
            if not available_dates:
                return None
            
            target_dt = DateUtils.parse_yyyymmdd(target_date)
            available_dates.sort()
            
            # 找到最接近的日期
            min_diff = float('inf')
            nearest_date = None
            
            for available_date in available_dates:
                available_dt = DateUtils.parse_yyyymmdd(available_date)
                diff = abs((target_dt - available_dt).days)
                
                if diff < min_diff:
                    min_diff = diff
                    nearest_date = available_date
                    
                # 如果差异超过7天，停止搜索
                if diff > 7:
                    break
            
            return nearest_date
            
        except Exception as e:
            logger.error(f"查找最近可用日期失败 {target_date}: {e}")
            return None
    
    def _find_nearest_trading_day(self, stock_id: str, target_date: str, available_dates: List[str] = None) -> Optional[str]:
        """
        查找最近的交易日
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            available_dates: 可用的日期列表，如果提供则直接使用而不查询数据库
            
        Returns:
            Optional[str]: 最近的交易日，如果找不到返回None
        """
        try:
            target_dt = DateUtils.parse_yyyymmdd(target_date)
            
            if available_dates:
                # 使用提供的可用日期列表
                min_diff = float('inf')
                nearest_date = None
                
                for available_date in available_dates:
                    available_dt = DateUtils.parse_yyyymmdd(available_date)
                    diff = abs((target_dt - available_dt).days)
                    
                    if diff < min_diff:
                        min_diff = diff
                        nearest_date = available_date
                        
                    # 如果差异超过7天，停止搜索
                    if diff > 7:
                        break
                
                return nearest_date
            else:
                # 回退到数据库查询（保持向后兼容）
                start_dt = target_dt - timedelta(days=7)
                end_dt = target_dt + timedelta(days=7)
                
                start_date = DateUtils.format_to_yyyymmdd(start_dt)
                end_date = DateUtils.format_to_yyyymmdd(end_dt)
                
                klines = self.data_loader.load_klines(stock_id, start_date=start_date, end_date=end_date)
                if not klines:
                    return None
                
                # 找到最接近目标日期的交易日
                min_diff = float('inf')
                nearest_date = None
                
                for kline in klines:
                    kline_date = kline.get('date', '')
                    if not kline_date:
                        continue
                        
                    kline_dt = DateUtils.parse_yyyymmdd(kline_date)
                    diff = abs((target_dt - kline_dt).days)
                    
                    if diff < min_diff:
                        min_diff = diff
                        nearest_date = kline_date
                
                return nearest_date
            
        except Exception as e:
            logger.error(f"查找最近交易日失败 {stock_id} {target_date}: {e}")
            return None
    
    def _get_incremental_klines_data(self, stock_id: str, dates: List[str], last_update_date: str, target_date: str) -> Dict[str, List[Dict]]:
        """
        情况2：获取增量K线数据（股票有过标签记录）
        
        Args:
            stock_id: 股票代码
            dates: 日期列表
            last_update_date: 上次更新日期
            target_date: 目标日期
            
        Returns:
            Dict[str, List[Dict]]: 按日期分组的K线数据
        """
        try:
            if not dates:
                return {}
            
            # 只获取从上次更新日期到目标日期的K线数据
            # 添加一些缓冲天数以确保有足够的数据用于计算（比如波动率需要历史数据）
            from datetime import datetime, timedelta
            start_date = DateUtils.get_date_before_days(last_update_date, 30)  # 往前推30天作为缓冲
            end_date = target_date
            
            # 只获取增量时间范围内的K线数据
            all_klines = self.data_loader.load_klines(stock_id, start_date=start_date, end_date=end_date)
            # 按日期分组，只保留需要的日期
            klines_by_date = {}
            for kline in all_klines:
                date = kline.get('date', '')
                if date in dates:
                    if date not in klines_by_date:
                        klines_by_date[date] = []
                    klines_by_date[date].append(kline)
            
            # 确保每个日期都有数据（即使为空列表）
            for date in dates:
                if date not in klines_by_date:
                    klines_by_date[date] = []
            
            return klines_by_date
            
        except Exception as e:
            logger.error(f"获取增量K线数据失败 {stock_id}: {e}")
            return {}
    
    def _save_stock_labels(self, stock_id: str, target_date: str, labels: List[str]):
        """
        保存股票标签到数据库
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            labels: 标签列表
        """
        try:
            if not labels:
                logger.warning(f"股票 {stock_id} 在 {target_date} 没有标签需要保存")
                return
            
            # 验证标签ID
            valid_labels = []
            for label_id in labels:
                if LabelMapping.validate_label_id(label_id):
                    valid_labels.append(label_id)
                else:
                    logger.warning(f"标签定义不存在: {label_id}")
            
            if not valid_labels:
                logger.warning(f"股票 {stock_id} 没有有效的标签")
                return
            
            # 保存到数据库
            self.data_loader.label_loader.upsert_stock_label(stock_id, target_date, valid_labels)
            
        except Exception as e:
            logger.error(f"保存股票标签失败 {stock_id} {target_date}: {e}")
    
    def _batch_save_stock_labels(self, labels_to_save: List[Dict[str, Any]]):
        """
        批量保存股票标签到数据库
        
        Args:
            labels_to_save: 要保存的标签数据列表
        """
        try:
            if not labels_to_save:
                return
            
            # 批量保存到数据库
            self.data_loader.label_loader.batch_save_stock_labels(labels_to_save)
            
            logger.info(f"批量保存了 {len(labels_to_save)} 条标签记录")
            
        except Exception as e:
            logger.error(f"批量保存股票标签失败: {e}")
            # 如果批量保存失败，回退到单个保存
            for label_data in labels_to_save:
                try:
                    self._save_stock_labels(
                        label_data['stock_id'], 
                        label_data['label_date'], 
                        label_data['labels']
                    )
                except Exception as single_error:
                    logger.error(f"单个保存标签失败 {label_data['stock_id']} {label_data['label_date']}: {single_error}")
    
    def _save_no_label_record(self, stock_id: str, target_date: str, categories: List[str], 
                             date_klines: List[Dict], all_klines_data: Dict[str, List[Dict]]):
        """
        记录无法计算标签的情况
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            categories: 尝试计算的标签分类
            date_klines: 当日K线数据
            all_klines_data: 所有K线数据
        """
        try:
            # 分析无法计算标签的原因
            reasons = []
            
            # 检查K线数据
            if not date_klines:
                reasons.append("当日无K线数据")
            elif len(date_klines) < 10:
                reasons.append(f"当日K线数据不足({len(date_klines)}条)")
            
            # 检查历史K线数据
            total_klines = sum(len(klines) for klines in all_klines_data.values() if klines)
            if total_klines < 100:
                reasons.append(f"历史K线数据不足({total_klines}条)")
            
            # 检查各个计算器的状态
            calculator_issues = []
            for category in categories:
                try:
                    calculator = self.get_calculator(category)
                    if not calculator:
                        calculator_issues.append(f"{category}:计算器未注册")
                    else:
                        # 尝试计算但不保存结果，检查是否有异常
                        all_klines_list = []
                        for date_klines in all_klines_data.values():
                            if date_klines:
                                all_klines_list.extend(date_klines)
                        
                        if all_klines_list:
                            labels = calculator.calculate_labels_for_stock(
                                stock_id, target_date, 
                                klines_data=all_klines_list,
                                data_loader=self.data_loader
                            )
                            if not labels:
                                calculator_issues.append(f"{category}:无标签生成")
                except Exception as e:
                    calculator_issues.append(f"{category}:计算异常({str(e)[:50]})")
            
            if calculator_issues:
                reasons.extend(calculator_issues)
            
            # 生成详细的失败原因
            failure_reason = "; ".join(reasons) if reasons else "未知原因"
            
            # 保存"no_label"标签，包含失败原因
            no_label_tag = f"no_label_{len(reasons)}_reasons"
            self._save_stock_labels(stock_id, target_date, [no_label_tag])
            
            # 记录详细的失败日志
            logger.warning(f"股票 {stock_id} 在 {target_date} 无法计算标签: {failure_reason}")
            
        except Exception as e:
            logger.error(f"❌ 记录无标签情况失败 {stock_id} {target_date}: {e}")
    
    
    # ============ 标签查询接口 ============
    
    def get_label_statistics(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取标签统计信息
        
        Args:
            target_date: 目标日期，默认为最新交易日
            
        Returns:
            Dict: 标签统计信息
        """
        try:
            if target_date is None:
                # 获取最新交易日
                target_date = self._get_latest_market_open_day()
            
            sql = """
            SELECT 
                COUNT(DISTINCT stock_id) as stock_count,
                COUNT(*) as label_count,
                COUNT(DISTINCT SUBSTRING_INDEX(labels, ',', 1)) as unique_labels
            FROM stock_labels
            WHERE label_date = %s
            """
            
            result = self.db.execute_query(sql, (target_date,))
            
            if result and len(result) > 0:
                stats = result[0]
                stats['target_date'] = target_date
                return stats
            else:
                return {
                    'target_date': target_date,
                    'stock_count': 0,
                    'label_count': 0,
                    'unique_labels': 0
                }
                
        except Exception as e:
            logger.error(f"获取标签统计信息失败: {e}")
            return {}
    
    def _get_latest_market_open_day(self) -> str:
        """
        获取最新交易日
        
        Returns:
            str: 最新交易日，格式为YYYYMMDD
        """
        try:
            # 这里可以从数据库或API获取最新交易日
            # 暂时返回当前日期作为默认值
            return DateUtils.get_current_date_str()
        except Exception as e:
            logger.error(f"获取最新交易日失败: {e}")
            return DateUtils.get_current_date_str()
    
    def get_stock_labels(self, stock_id: str, target_date: Optional[str] = None) -> List[str]:
        """
        获取股票的标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期，默认为最新交易日
            
        Returns:
            List[str]: 标签列表
        """
        try:
            if target_date is None:
                target_date = self._get_latest_market_open_day()
            
            sql = """
            SELECT labels
            FROM stock_labels
            WHERE stock_id = %s AND label_date = %s
            """
            
            result = self.db.execute_query(sql, (stock_id, target_date))
            
            if result and len(result) > 0 and result[0]['labels']:
                labels_str = result[0]['labels']
                return [label.strip() for label in labels_str.split(',') if label.strip()]
            else:
                return []
                
        except Exception as e:
            logger.error(f"获取股票标签失败 {stock_id}: {e}")
            return []
    
    def get_labels_by_date_range(self, start_date: str, end_date: str, 
                                label_categories: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
        """
        按日期范围获取标签数据
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            label_categories: 标签分类过滤，为None时获取所有分类
            
        Returns:
            Dict: 按日期分组的标签数据
        """
        try:
            # 构建SQL查询
            if label_categories:
                # 需要根据分类过滤标签
                category_labels = []
                for category in label_categories:
                    category_labels.extend(LabelMapping.get_labels_by_category(category).keys())
                
                if category_labels:
                    label_filter = " AND (" + " OR ".join([f"labels LIKE '%{label}%'" for label in category_labels]) + ")"
                else:
                    return {}
            else:
                label_filter = ""
            
            sql = f"""
            SELECT stock_id, label_date, labels
            FROM stock_labels
            WHERE label_date >= %s AND label_date <= %s{label_filter}
            ORDER BY label_date, stock_id
            """
            
            result = self.db.execute_query(sql, (start_date, end_date))
            
            # 按日期分组
            labels_by_date = {}
            for row in result:
                date = row['label_date']
                if date not in labels_by_date:
                    labels_by_date[date] = []
                
                labels_list = [label.strip() for label in row['labels'].split(',') if label.strip()]
                labels_by_date[date].append({
                    'stock_id': row['stock_id'],
                    'labels': labels_list
                })
            
            return labels_by_date
            
        except Exception as e:
            logger.error(f"按日期范围获取标签失败: {e}")
            return {}
    
    def evaluate_quality(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        评估标签质量
        
        Args:
            target_date: 目标日期 (YYYYMMDD格式)
            
        Returns:
            Dict: 标签质量评估结果
        """
        # TODO: 实现标签质量评估功能
        return {"status": "not_implemented"}
    
    # ============ 标签映射查询接口 ============
    
    def get_all_labels(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有标签定义
        
        Returns:
            Dict: 所有标签定义
        """
        return LabelMapping.get_all_labels()
    
    def get_labels_by_category(self, category: str) -> Dict[str, Dict[str, Any]]:
        """
        按分类获取标签定义
        
        Args:
            category: 标签分类
            
        Returns:
            Dict: 该分类下的标签定义
        """
        return LabelMapping.get_labels_by_category(category)
    
    def get_categories(self) -> Dict[str, str]:
        """
        获取所有标签分类
        
        Returns:
            Dict: 标签分类映射
        """
        return LabelMapping.get_categories()
    
    def validate_label_id(self, label_id: str) -> bool:
        """
        验证标签ID是否有效
        
        Args:
            label_id: 标签ID
            
        Returns:
            bool: 是否有效
        """
        return LabelMapping.validate_label_id(label_id)
    
    # ============ 配置管理接口 ============
    
    def get_sorted_categories_by_priority(self) -> list:
        """
        按优先级排序的标签分类列表
        
        Returns:
            list: 按优先级排序的标签分类列表
        """
        return LabelConfig.get_sorted_categories_by_priority()
    
    def refresh_all_labels(self, last_market_open_day: str):
        """
        刷新所有股票标签（便捷方法）
        
        用于以下场景：
        - 添加新的标签计算器后需要重新计算所有标签
        - 修改标签定义后需要重新计算
        - 数据修复后需要重新计算标签
        
        Args:
            last_market_open_day: 最新交易日
        """
        logger.info("🔄 开始刷新所有股票标签...")
        self.renew(last_market_open_day, is_refresh=True)
