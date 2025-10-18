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

import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date, timedelta
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
        self.data_loader = DataLoader(db)
        
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
            # 生成更新任务
            update_jobs = self._generate_update_jobs(last_market_open_day, is_refresh)
            if not update_jobs:
                logger.info("📋 没有需要更新的标签任务")
                return
            
            logger.info(f"📋 生成了 {len(update_jobs)} 个标签更新任务")
            
            # 执行更新任务
            self._execute_update_jobs(update_jobs, last_market_open_day)
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ 标签数据更新完成: {last_market_open_day}, 耗时 {elapsed_time:.2f} 秒")
            
        except Exception as e:
            logger.error(f"❌ 标签数据更新失败: {e}")
            raise e
    
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
            current_dt = datetime.strptime(last_market_open_day, '%Y%m%d')
            
            for stock in all_stocks:
                stock_id = stock['id']
                last_update_date = stock_last_update_dates.get(stock_id)
                
                if last_update_date is None:
                    # 从未更新过，需要更新
                    stocks_needing_update.append(stock)
                    continue
                
                # 计算距离上次更新的天数
                last_update_dt = datetime.strptime(last_update_date, '%Y%m%d')
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
                    labels_count = result.get('dates_count', 0)
                    progress = int(i * 100 / total_jobs)
                    
                    if labels_count > 0:
                        logger.info(f"股票 {stock_id} ({stock_name}) 计算完毕，更新{labels_count}个标签 总进度 {progress}%")
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
            enable_monitoring=True,
            timeout=1200.0,  # 20分钟超时
            is_verbose=True
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
        计算单只股票的所有标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            categories: 需要计算的标签分类
            
        Returns:
            Dict: 计算结果
        """
        try:
            # 生成历史日期列表
            historical_dates = self._generate_historical_dates(stock_id, target_date)
            
            # 如果没有需要计算的日期，直接返回
            if not historical_dates:
                return {'success': True, 'labels_saved': 0}
            
            total_labels_saved = 0
            
            # 根据股票情况智能获取K线数据
            all_klines_data = self._get_stock_klines_data_optimized(stock_id, historical_dates, target_date)
            
            # 为每个历史日期计算标签
            for date in historical_dates:
                all_labels = []
                
                # 获取该日期的K线数据
                date_klines = all_klines_data.get(date, [])
                if not date_klines:
                    continue
                
                for category in categories:
                    try:
                        # 获取对应的计算器
                        calculator = self.get_calculator(category)
                        if calculator:
                            # 传递K线数据给计算器，避免重复查询
                            labels = calculator.calculate_labels_for_stock(
                                stock_id, date, 
                                klines_data=date_klines,
                                data_loader=self.data_loader
                            )
                            if labels:
                                all_labels.extend(labels)
                                
                    except Exception as e:
                        continue
                
                # 保存该日期的标签到数据库
                if all_labels:
                    self._save_stock_labels(stock_id, date, all_labels)
                    total_labels_saved += 1
            
            return {
                'stock_id': stock_id,
                'dates_count': total_labels_saved,
                'total_dates': len(historical_dates),
                'categories': categories
            }
            
        except Exception as e:
            logger.error(f"❌ 股票 {stock_id} 标签计算异常: {e}")
            raise e
    
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
            
            # 从上次更新时间向后30天，找到对应的K线数据截止日期
            last_update_dt = datetime.strptime(last_update_date, '%Y%m%d')
            next_update_dt = last_update_dt + timedelta(days=30)
            
            # 查找这个日期附近的最后一个交易日
            nearest_trading_day = self._find_nearest_trading_day(stock_id, next_update_dt.strftime('%Y%m%d'))
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
            
            start_dt = datetime.strptime(earliest_date, '%Y%m%d')
            end_dt = datetime.strptime(target_date, '%Y%m%d')
            
            dates = []
            current_dt = start_dt
            
            # 从最早日期开始，每30天生成一个标签
            while current_dt <= end_dt:
                dates.append(current_dt.strftime('%Y%m%d'))
                current_dt += timedelta(days=30)  # 每1个月
            
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
            
            start_dt = datetime.strptime(last_update_date, '%Y%m%d')
            end_dt = datetime.strptime(target_date, '%Y%m%d')
            
            dates = []
            current_dt = start_dt + timedelta(days=30)  # 从上次更新后30天开始
            
            # 从上次更新日期开始，每30天生成一个标签，直到目标日期
            while current_dt <= end_dt:
                dates.append(current_dt.strftime('%Y%m%d'))
                current_dt += timedelta(days=30)  # 每1个月
            
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
                    return earliest_date.strftime('%Y%m%d')
            
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
            
            # 计算日期范围
            start_date = min(dates)
            end_date = max(dates)
            
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
            
            target_dt = datetime.strptime(target_date, '%Y%m%d')
            available_dates.sort()
            
            # 找到最接近的日期
            min_diff = float('inf')
            nearest_date = None
            
            for available_date in available_dates:
                available_dt = datetime.strptime(available_date, '%Y%m%d')
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
    
    def _find_nearest_trading_day(self, stock_id: str, target_date: str) -> Optional[str]:
        """
        查找最近的交易日
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            
        Returns:
            Optional[str]: 最近的交易日，如果找不到返回None
        """
        try:
            # 尝试获取目标日期前7天到后7天的K线数据
            target_dt = datetime.strptime(target_date, '%Y%m%d')
            start_dt = target_dt - timedelta(days=7)
            end_dt = target_dt + timedelta(days=7)
            
            start_date = start_dt.strftime('%Y%m%d')
            end_date = end_dt.strftime('%Y%m%d')
            
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
                    
                kline_dt = datetime.strptime(kline_date, '%Y%m%d')
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
            start_dt = datetime.strptime(last_update_date, '%Y%m%d') - timedelta(days=30)  # 往前推30天作为缓冲
            end_dt = datetime.strptime(target_date, '%Y%m%d')
            
            start_date = start_dt.strftime('%Y%m%d')
            end_date = end_dt.strftime('%Y%m%d')
            
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
            return datetime.now().strftime('%Y%m%d')
        except Exception as e:
            logger.error(f"获取最新交易日失败: {e}")
            return datetime.now().strftime('%Y%m%d')
    
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
