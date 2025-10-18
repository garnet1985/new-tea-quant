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
        
        # 初始化计算器注册表
        self.registry = LabelCalculatorRegistry()
        self._register_calculators()
        
        # 缓存计算器实例
        self._calculator_instances = {}
        
        logger.info("✅ 标签服务初始化完成")
    
    def _register_calculators(self):
        """注册所有标签计算器"""
        self.registry.register_calculator('market_cap', MarketCapLabelCalculator)
        self.registry.register_calculator('industry', IndustryLabelCalculator)
        self.registry.register_calculator('volatility', VolatilityLabelCalculator)
        self.registry.register_calculator('volume', VolumeLabelCalculator)
        self.registry.register_calculator('financial', FinancialLabelCalculator)
        
        logger.info(f"✅ 已注册 {len(self.registry._calculators)} 个标签计算器")
    
    def get_calculator(self, category: str) -> Optional[BaseLabelCalculator]:
        """
        获取指定分类的计算器实例
        
        Args:
            category: 标签分类
            
        Returns:
            BaseLabelCalculator: 计算器实例
        """
        if category not in self._calculator_instances:
            calculator_class = self.registry.get_calculator(category)
            if calculator_class:
                self._calculator_instances[category] = calculator_class(self.data_loader)
            else:
                logger.warning(f"未找到标签分类 {category} 的计算器")
                return None
        
        return self._calculator_instances.get(category)
    
    # ============ 标签数据更新接口 ============
    
    def renew(self, last_market_open_day: str, force_update: bool = False):
        """
        标签数据增量更新
        
        Args:
            last_market_open_day: 最新交易日
            force_update: 是否强制更新所有股票
        """
        logger.info(f"🔄 开始标签数据增量更新: {last_market_open_day}, 强制更新: {force_update}")
        
        try:
            # 生成更新任务
            update_jobs = self._generate_update_jobs(last_market_open_day, force_update)
            if not update_jobs:
                logger.info("📋 没有需要更新的标签任务")
                return
            
            logger.info(f"📋 生成了 {len(update_jobs)} 个标签更新任务")
            
            # 执行更新任务
            self._execute_update_jobs(update_jobs, last_market_open_day)
            
            logger.info(f"✅ 标签数据增量更新完成: {last_market_open_day}")
            
        except Exception as e:
            logger.error(f"❌ 标签数据增量更新失败: {e}")
            raise e
    
    def _generate_update_jobs(self, last_market_open_day: str, force_update: bool = False) -> List[Dict[str, Any]]:
        """
        生成更新任务列表
        
        Args:
            last_market_open_day: 最新交易日
            force_update: 是否强制更新
            
        Returns:
            List[Dict]: 任务列表
        """
        jobs = []
        
        # 获取所有股票列表
        stock_list_table = self.db.get_table_instance('stock_list')
        all_stocks = stock_list_table.load_filtered_stock_list()
        all_stock_ids = [stock['id'] for stock in all_stocks]
        
        # 获取需要计算的标签分类
        categories_to_calculate = []
        for category in LabelMapping.get_categories().keys():
            if not LabelConfig.is_static_category(category):
                categories_to_calculate.append(category)
        
        if force_update:
            logger.info(f"🔄 强制更新模式：{len(all_stock_ids)}只股票")
            stocks_to_process = all_stock_ids
        else:
            # 增量更新模式：只更新需要更新的股票
            stocks_needing_update = []
            for stock_id in all_stock_ids:
                if self._stock_needs_incremental_update(stock_id, last_market_open_day):
                    stocks_needing_update.append(stock_id)
            
            if stocks_needing_update:
                logger.info(f"📋 增量更新模式：{len(stocks_needing_update)}只股票需要更新")
                stocks_to_process = stocks_needing_update
            else:
                logger.info("📋 没有股票需要更新")
                return []
        
        # 生成任务
        for stock_id in stocks_to_process:
            jobs.append({
                'id': stock_id,  # FuturesWorker期望的字段名
                'data': {
                    'stock_id': stock_id,
                    'target_date': last_market_open_day,
                    'categories': categories_to_calculate
                }
            })
        
        return jobs
    
    def _stock_needs_incremental_update(self, stock_id: str, last_market_open_day: str) -> bool:
        """
        判断股票是否需要增量更新
        
        Args:
            stock_id: 股票代码
            last_market_open_day: 最新交易日
            
        Returns:
            bool: 是否需要更新
        """
        last_update_date = self._get_stock_last_label_update_date(stock_id)
        
        if last_update_date is None:
            return True  # 从未更新过，需要更新
        
        # 计算距离上次更新的天数
        last_update_dt = datetime.strptime(last_update_date, '%Y%m%d')
        current_dt = datetime.strptime(last_market_open_day, '%Y%m%d')
        days_since_update = (current_dt - last_update_dt).days
        
        return LabelConfig.should_update_stock(days_since_update)
    
    def _get_stock_last_label_update_date(self, stock_id: str) -> Optional[str]:
        """
        获取股票的最后标签更新日期
        
        Args:
            stock_id: 股票代码
            
        Returns:
            str: 最后更新日期，格式为YYYYMMDD
        """
        try:
            sql = """
            SELECT MAX(label_date) as last_update_date
            FROM stock_labels
            WHERE stock_id = %s
            """
            result = self.db.execute_query(sql, (stock_id,))
            
            if result and len(result) > 0 and result[0]['last_update_date']:
                last_date = result[0]['last_update_date']
                if isinstance(last_date, date):
                    return last_date.strftime('%Y%m%d')
                else:
                    return str(last_date).replace('-', '')
            
            return None
            
        except Exception as e:
            logger.error(f"获取股票最后更新日期失败 {stock_id}: {e}")
            return None
    
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
        
        for job in jobs:
            try:
                result = self._calculate_single_stock_labels_wrapper(job['data'])
                if result['status'] == 'success':
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ 任务执行失败: {e}")
        
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
        
        # 创建多线程工作器
        worker = FuturesWorker(
            max_workers=max_workers,
            execution_mode=ThreadExecutionMode.PARALLEL,
            job_executor=self._calculate_single_stock_labels_wrapper,
            enable_monitoring=True,
            timeout=1200.0,  # 20分钟超时
            is_verbose=True
        )
        
        # 执行任务
        stats = worker.run_jobs(jobs)
        worker.print_stats()
        
        logger.info(f"✅ 多线程执行完成: 成功 {stats.get('success_count', 0)}, 失败 {stats.get('failed_count', 0)}")
    
    def _calculate_single_stock_labels_wrapper(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        单股票标签计算包装器（适配FuturesWorker）
        
        Args:
            job_data: 任务数据
            
        Returns:
            Dict: 执行结果
        """
        stock_id = job_data['stock_id']
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
            logger.debug(f"股票 {stock_id} 需要计算 {len(historical_dates)} 个历史时间点的标签")
            
            total_labels_saved = 0
            
            # 一次性获取股票的所有历史数据
            all_klines_data = self._get_stock_all_klines_data(stock_id, historical_dates)
            
            # 为每个历史日期计算标签
            for date in historical_dates:
                all_labels = []
                
                # 获取该日期的K线数据
                date_klines = all_klines_data.get(date, [])
                if not date_klines:
                    logger.warning(f"股票 {stock_id} 在 {date} 没有K线数据")
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
                        logger.warning(f"股票 {stock_id} {category} 在 {date} 标签计算失败: {e}")
                        continue
                
                # 保存该日期的标签到数据库
                if all_labels:
                    self._save_stock_labels(stock_id, date, all_labels)
                    total_labels_saved += 1
            
            logger.debug(f"✅ 股票 {stock_id} 历史标签计算完成: {total_labels_saved}个时间点")
            
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
        生成历史日期列表（每1个月一个点）
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            
        Returns:
            List[str]: 日期列表
        """
        try:
            from datetime import datetime, timedelta
            
            # 获取股票的最早数据日期
            earliest_date = self._get_stock_earliest_date(stock_id)
            if not earliest_date:
                logger.warning(f"无法获取股票 {stock_id} 的最早数据日期")
                return [target_date]
            
            start_dt = datetime.strptime(earliest_date, '%Y%m%d')
            end_dt = datetime.strptime(target_date, '%Y%m%d')
            
            dates = []
            current_dt = start_dt
            
            while current_dt <= end_dt:
                dates.append(current_dt.strftime('%Y%m%d'))
                current_dt += timedelta(days=30)  # 每1个月
            
            # 确保目标日期在列表中
            if target_date not in dates:
                dates.append(target_date)
            
            return sorted(dates)
            
        except Exception as e:
            logger.error(f"生成历史日期失败 {stock_id}: {e}")
            return [target_date]
    
    def _get_stock_earliest_date(self, stock_id: str) -> Optional[str]:
        """
        获取股票的最早数据日期
        
        Args:
            stock_id: 股票代码
            
        Returns:
            str: 最早日期，格式为YYYYMMDD
        """
        try:
            sql = """
            SELECT MIN(date) as earliest_date
            FROM stock_kline
            WHERE id = %s
            """
            result = self.db.execute_query(sql, (stock_id,))
            
            if result and len(result) > 0 and result[0]['earliest_date']:
                earliest_date = result[0]['earliest_date']
                if isinstance(earliest_date, datetime):
                    return earliest_date.strftime('%Y%m%d')
                else:
                    return str(earliest_date).replace('-', '')
            
            return None
            
        except Exception as e:
            logger.error(f"获取股票最早日期失败 {stock_id}: {e}")
            return None
    
    def _get_stock_all_klines_data(self, stock_id: str, dates: List[str]) -> Dict[str, List[Dict]]:
        """
        批量获取股票在所有指定日期的K线数据
        
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
            
            # 按日期分组
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
            
            logger.debug(f"股票 {stock_id} 获取了 {len(klines_by_date)} 个日期的K线数据")
            return klines_by_date
            
        except Exception as e:
            logger.error(f"批量获取股票K线数据失败 {stock_id}: {e}")
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
            self._upsert_stock_label(stock_id, target_date, valid_labels)
            
        except Exception as e:
            logger.error(f"保存股票标签失败 {stock_id} {target_date}: {e}")
    
    def _upsert_stock_label(self, stock_id: str, target_date: str, labels: List[str]):
        """
        插入或更新股票标签记录
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            labels: 标签列表
        """
        try:
            # 将标签列表转换为逗号分隔的字符串
            labels_str = ','.join(labels)
            
            sql = """
            INSERT INTO stock_labels (stock_id, label_date, labels, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            ON DUPLICATE KEY UPDATE
                labels = %s,
                updated_at = NOW()
            """
            
            self.db.execute_query(sql, (stock_id, target_date, labels_str, labels_str))
            
        except Exception as e:
            logger.error(f"插入股票标签记录失败 {stock_id} {target_date}: {e}")
    
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
