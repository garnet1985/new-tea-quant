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
- LabelDefinitions: 标签定义管理
- LabelEvaluator: 标签质量评估
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date, timedelta
import pandas as pd
from loguru import logger
from .base_calculator import BaseLabelCalculator, LabelCalculatorRegistry
from .calculators import (
    MarketCapLabelCalculator, 
    IndustryLabelCalculator, 
    VolatilityLabelCalculator,
    VolumeLabelCalculator,
    FinancialLabelCalculator
)
from .label_mapping import LabelMapping
from .definitions import LabelDefinitions
from .evaluator import LabelEvaluator
from .conf.config import LabelConfig, UpdateFrequency
from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader


class LabelerService:
    """
    股票标签服务（主入口）
    
    职责：
    - 提供统一的标签计算API
    - 管理标签计算任务
    - 协调各个标签计算器
    - 提供标签映射查询接口
    """
    
    def __init__(self, db: DatabaseManager = None):
        """
        初始化标签服务
        
        Args:
            db: 数据库管理器实例
        """
        if db is None:
            db = DatabaseManager()
            db.initialize()
        
        self.db = db
        self.data_loader = DataLoader(db)
        self.label_definitions = LabelDefinitions(db)
        self.label_evaluator = LabelEvaluator(self.db)
        
        # 初始化计算器注册表
        self.registry = LabelCalculatorRegistry()
        self._register_calculators()
        
        # 缓存计算器实例
        self._calculator_instances = {}
        
        # 初始化标签定义
        self._initialize_label_definitions()
    
    def _register_calculators(self):
        """注册所有标签计算器"""
        # 注册各种标签计算器
        self.registry.register_calculator(MarketCapLabelCalculator, 'market_cap')
        self.registry.register_calculator(IndustryLabelCalculator, 'industry')
        self.registry.register_calculator(VolatilityLabelCalculator, 'volatility')
        self.registry.register_calculator(VolumeLabelCalculator, 'volume')
        self.registry.register_calculator(FinancialLabelCalculator, 'financial')
        
        logger.info(f"已注册 {len(self.registry.get_all_categories())} 个标签计算器")
    
    def _initialize_label_definitions(self):
        """初始化标签定义"""
        try:
            logger.info("🔄 初始化标签定义...")
            self.label_definitions.initialize_default_definitions()
            logger.info("✅ 标签定义初始化完成")
        except Exception as e:
            logger.warning(f"标签定义初始化失败: {e}")
            # 不抛出异常，允许系统继续运行
    
    def get_calculator(self, category: str) -> BaseLabelCalculator:
        """
        获取标签计算器实例
        
        Args:
            category: 标签分类
            
        Returns:
            BaseLabelCalculator: 计算器实例
        """
        if category not in self._calculator_instances:
            self._calculator_instances[category] = self.registry.get_calculator(
                category, self.data_loader, self.label_definitions
            )
        return self._calculator_instances[category]
    
    def calculate_stock_labels(self, stock_id: str, target_date: str, categories: Optional[List[str]] = None) -> List[str]:
        """
        计算单只股票的标签
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期 (YYYYMMDD格式)
            categories: 要计算的标签分类，None表示计算所有分类
            
        Returns:
            List[str]: 标签ID列表
        """
        all_labels = []
        
        # 确定要计算的分类
        if categories is None:
            categories = self.registry.get_all_categories()
        
        for category in categories:
            try:
                calculator = self.get_calculator(category)
                labels = calculator.calculate_labels_for_stock(stock_id, target_date)
                all_labels.extend(labels)
            except Exception as e:
                logger.error(f"计算 {category} 标签失败 {stock_id}: {e}")
        
        return all_labels
    
    def batch_calculate_labels(self, stock_ids: List[str], target_date: str, categories: Optional[List[str]] = None):
        """
        批量计算股票标签
        
        Args:
            stock_ids: 股票代码列表
            target_date: 目标日期 (YYYYMMDD格式)
            categories: 要计算的标签分类
        """
        logger.info(f"开始批量计算标签: {len(stock_ids)}只股票, 日期: {target_date}, 分类: {categories}")
        
        if not stock_ids:
            logger.warning("股票列表为空，跳过标签计算")
            return
        
        # 确定要计算的分类
        if categories is None:
            categories = self.registry.get_all_categories()
        
        # 按优先级排序分类
        sorted_categories = sorted(categories, key=lambda x: self.get_priority(x))
        
        success_count = 0
        error_count = 0
        
        for stock_id in stock_ids:
            try:
                # 计算股票的所有标签
                labels = self.calculate_stock_labels(stock_id, target_date, sorted_categories)
                
                # 存储标签到数据库
                if labels:
                    self._save_stock_labels(stock_id, target_date, labels)
                    success_count += 1
                else:
                    logger.debug(f"股票 {stock_id} 没有计算到任何标签")
                    success_count += 1  # 没有标签也是正常的
                    
            except Exception as e:
                logger.error(f"计算股票 {stock_id} 标签失败: {e}")
                error_count += 1
        
        logger.info(f"批量标签计算完成: 成功 {success_count}, 失败 {error_count}")
    
    def _save_stock_labels(self, stock_id: str, target_date: str, labels: List[str]):
        """
        保存股票标签到数据库
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            labels: 标签ID列表
        """
        try:
            for label_id in labels:
                # 检查标签定义是否存在
                if not LabelMapping.get_label_by_id(label_id):
                    logger.warning(f"标签定义不存在: {label_id}")
                    continue
                
                # 插入或更新标签记录
                self._upsert_stock_label(stock_id, target_date, label_id)
                
        except Exception as e:
            logger.error(f"保存股票标签失败 {stock_id} {target_date}: {e}")
    
    def _upsert_stock_label(self, stock_id: str, target_date: str, label_id: str):
        """
        插入或更新股票标签记录
        
        Args:
            stock_id: 股票代码
            target_date: 目标日期
            label_id: 标签ID
        """
        try:
            # 使用UPSERT语句（MySQL的ON DUPLICATE KEY UPDATE）
            sql = """
            INSERT INTO stock_labels (stock_id, label_id, label_date, created_at, updated_at)
            VALUES (%s, %s, %s, NOW(), NOW())
            ON DUPLICATE KEY UPDATE 
                updated_at = NOW()
            """
            
            self.db.execute_query(sql, (stock_id, label_id, target_date))
            
        except Exception as e:
            logger.error(f"更新股票标签记录失败 {stock_id} {label_id} {target_date}: {e}")
            raise e
    
    def update_monthly_labels(self, target_date: Optional[str] = None):
        """
        更新月度标签
        
        Args:
            target_date: 目标日期 (YYYYMMDD格式)，None表示当前月份
        """
        if target_date is None:
            target_date = datetime.now().replace(day=1).strftime('%Y%m%d')
        
        logger.info(f"开始更新月度标签: {target_date}")
        
        # 获取所有股票
        stock_list_table = self.db.get_table_instance('stock_list')
        stocks = stock_list_table.load_filtered_stock_list()
        stock_ids = [stock['id'] for stock in stocks]
        
        # 批量计算标签
        self.batch_calculate_labels(stock_ids, target_date)
        
        logger.info(f"月度标签更新完成: {target_date}")
    
    def renew(self, last_market_open_day: str, force_update: bool = False):
        """
        标签数据更新接口（供start.py调用）
        
        Args:
            last_market_open_day: 最新交易日 (YYYYMMDD格式)
            force_update: 是否强制更新所有标签，默认False（按频率更新）
        """
        logger.info(f"🔄 开始标签数据更新: {last_market_open_day}, 强制更新: {force_update}")
        
        try:
            if force_update:
                # 强制更新所有标签
                self._renew_all_labels(last_market_open_day)
            else:
                # 按频率更新标签
                self._renew_labels_by_frequency(last_market_open_day)
            
            logger.info(f"✅ 标签数据更新完成: {last_market_open_day}")
            
        except Exception as e:
            logger.error(f"❌ 标签数据更新失败: {e}")
            raise e
    
    def _renew_all_labels(self, target_date: str):
        """
        强制更新所有标签
        
        Args:
            target_date: 目标日期 (YYYYMMDD格式)
        """
        logger.info("🔄 强制更新所有标签分类")
        
        # 获取所有股票
        stock_list_table = self.db.get_table_instance('stock_list')
        stocks = stock_list_table.load_filtered_stock_list()
        stock_ids = [stock['id'] for stock in stocks]
        
        # 按优先级顺序更新所有标签分类
        categories = self.get_sorted_categories_by_priority()
        available_categories = [cat for cat in categories if cat in self.get_available_categories()]
        
        for category in available_categories:
            logger.info(f"🔄 更新 {category} 标签分类")
            self.batch_calculate_labels(stock_ids, target_date, [category])
    
    def _renew_labels_by_frequency(self, last_market_open_day: str):
        """
        按频率更新标签
        
        Args:
            last_market_open_day: 最新交易日 (YYYYMMDD格式)
        """
        logger.info("🔄 按频率更新标签")
        
        # 生成更新任务列表
        update_jobs = self._generate_update_jobs(last_market_open_day)
        
        if not update_jobs:
            logger.info("⏭️ 没有需要更新的标签任务")
            return
        
        # 执行更新任务
        for job in update_jobs:
            self._execute_update_job(job)
    
    def _generate_update_jobs(self, last_market_open_day: str) -> List[Dict[str, Any]]:
        """
        生成标签更新任务列表
        
        Args:
            last_market_open_day: 最新交易日
            
        Returns:
            List[Dict]: 更新任务列表
        """
        jobs = []
        
        # 按优先级顺序处理各频率的标签
        frequencies = [UpdateFrequency.DAILY, UpdateFrequency.WEEKLY, UpdateFrequency.MONTHLY, 
                      UpdateFrequency.QUARTERLY, UpdateFrequency.YEARLY]
        
        for frequency in frequencies:
            categories = self.get_categories_by_frequency(frequency)
            available_categories = [cat for cat in categories if cat in self.get_available_categories()]
            
            if available_categories:
                # 检查是否需要更新
                if self._should_update_frequency(frequency, last_market_open_day):
                    # 获取需要更新的股票列表
                    stocks_to_update = self._get_stocks_needing_update(available_categories, last_market_open_day)
                    
                    if stocks_to_update:
                        job = {
                            'frequency': frequency,
                            'categories': available_categories,
                            'stocks': stocks_to_update,
                            'target_date': last_market_open_day
                        }
                        jobs.append(job)
                        logger.info(f"📋 生成更新任务: {frequency.value} - {len(stocks_to_update)}只股票")
                    else:
                        logger.info(f"⏭️ {frequency.value} 频率没有股票需要更新")
                else:
                    logger.info(f"⏭️ 跳过 {frequency.value} 频率的标签更新")
        
        return jobs
    
    def _get_stocks_needing_update(self, categories: List[str], last_market_open_day: str) -> List[str]:
        """
        获取需要更新的股票列表
        
        Args:
            categories: 标签分类列表
            last_market_open_day: 最新交易日
            
        Returns:
            List[str]: 需要更新的股票代码列表
        """
        try:
            # 获取所有股票
            stock_list_table = self.db.get_table_instance('stock_list')
            all_stocks = stock_list_table.load_filtered_stock_list()
            all_stock_ids = [stock['id'] for stock in all_stocks]
            
            # 检查每个股票是否需要更新标签
            stocks_needing_update = []
            
            for stock_id in all_stock_ids:
                if self._stock_needs_label_update(stock_id, categories, last_market_open_day):
                    stocks_needing_update.append(stock_id)
            
            return stocks_needing_update
            
        except Exception as e:
            logger.error(f"获取需要更新的股票列表失败: {e}")
            return []
    
    def _stock_needs_label_update(self, stock_id: str, categories: List[str], last_market_open_day: str) -> bool:
        """
        检查股票是否需要更新标签
        
        Args:
            stock_id: 股票代码
            categories: 标签分类列表
            last_market_open_day: 最新交易日
            
        Returns:
            bool: 是否需要更新
        """
        try:
            # 这里可以添加更复杂的逻辑，例如：
            # 1. 检查股票标签的最后更新时间
            # 2. 检查股票数据是否有变化
            # 3. 检查标签计算依赖的数据是否更新
            
            # 目前简化实现：检查是否存在该日期的标签数据
            for category in categories:
                # 检查是否存在该股票在该日期的该分类标签
                if not self._has_label_for_date(stock_id, category, last_market_open_day):
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"检查股票 {stock_id} 标签更新需求失败: {e}")
            return True  # 出错时默认需要更新
    
    def _has_label_for_date(self, stock_id: str, category: str, target_date: str) -> bool:
        """
        检查股票在指定日期是否有指定分类的标签
        
        Args:
            stock_id: 股票代码
            category: 标签分类
            target_date: 目标日期
            
        Returns:
            bool: 是否存在标签
        """
        try:
            # 查询数据库检查是否存在标签记录
            sql = """
            SELECT COUNT(*) as count
            FROM stock_labels sl
            JOIN label_definitions ld ON sl.label_id = ld.label_id
            WHERE sl.stock_id = %s 
            AND ld.label_category = %s
            AND sl.label_date = %s
            """
            
            result = self.db.execute_query(sql, (stock_id, category, target_date))
            
            if result and len(result) > 0:
                return result[0]['count'] > 0
            
            return False
            
        except Exception as e:
            logger.warning(f"检查标签存在性失败 {stock_id} {category} {target_date}: {e}")
            return False
    
    def _execute_update_job(self, job: Dict[str, Any]):
        """
        执行标签更新任务
        
        Args:
            job: 更新任务
        """
        try:
            frequency = job['frequency']
            categories = job['categories']
            stocks = job['stocks']
            target_date = job['target_date']
            
            logger.info(f"🔄 执行更新任务: {frequency.value} - {len(stocks)}只股票 - {categories}")
            
            # 批量计算标签
            self.batch_calculate_labels(stocks, target_date, categories)
            
            logger.info(f"✅ 完成更新任务: {frequency.value} - {len(stocks)}只股票")
            
        except Exception as e:
            logger.error(f"❌ 执行更新任务失败: {e}")
            raise e
    
    def _should_update_frequency(self, frequency: UpdateFrequency, target_date: str) -> bool:
        """
        判断是否需要更新指定频率的标签
        
        Args:
            frequency: 更新频率
            target_date: 目标日期
            
        Returns:
            bool: 是否需要更新
        """
        try:
            # 这里可以添加更复杂的逻辑来判断是否需要更新
            # 例如检查上次更新时间、检查数据是否有变化等
            
            if frequency == UpdateFrequency.DAILY:
                return True  # 每日都更新
            
            elif frequency == UpdateFrequency.WEEKLY:
                # 每周更新（例如每周一）
                from datetime import datetime
                date_obj = datetime.strptime(target_date, '%Y%m%d')
                return date_obj.weekday() == 0  # 周一
            
            elif frequency == UpdateFrequency.MONTHLY:
                # 每月更新（例如每月1号）
                from datetime import datetime
                date_obj = datetime.strptime(target_date, '%Y%m%d')
                return date_obj.day == 1
            
            elif frequency == UpdateFrequency.QUARTERLY:
                # 每季度更新（例如每季度第一天）
                from datetime import datetime
                date_obj = datetime.strptime(target_date, '%Y%m%d')
                return date_obj.day == 1 and date_obj.month in [1, 4, 7, 10]
            
            elif frequency == UpdateFrequency.YEARLY:
                # 每年更新（例如每年1月1号）
                from datetime import datetime
                date_obj = datetime.strptime(target_date, '%Y%m%d')
                return date_obj.month == 1 and date_obj.day == 1
            
            else:
                return False
                
        except Exception as e:
            logger.warning(f"判断更新频率失败: {e}")
            return True  # 出错时默认更新
    
    def get_label_statistics(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        获取标签统计信息
        
        Args:
            target_date: 目标日期 (YYYYMMDD格式)
            
        Returns:
            Dict: 标签统计信息
        """
        return self.data_loader.label_loader.get_label_statistics(target_date)
    
    def evaluate_label_quality(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        评估标签质量
        
        Args:
            target_date: 目标日期 (YYYYMMDD格式)
            
        Returns:
            Dict: 标签质量评估结果
        """
        return self.label_evaluator.evaluate_quality(target_date)
    
    # ============ 标签映射查询接口 ============
    
    def get_all_labels(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有标签定义
        
        Returns:
            Dict[str, Dict[str, Any]]: 所有标签定义
        """
        return LabelMapping.get_all_labels()
    
    def get_labels_by_category(self, category: str) -> Dict[str, Dict[str, Any]]:
        """
        根据分类获取标签
        
        Args:
            category: 标签分类
            
        Returns:
            Dict[str, Dict[str, Any]]: 该分类下的标签定义
        """
        return LabelMapping.get_labels_by_category(category)
    
    def get_label_by_id(self, label_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取标签定义
        
        Args:
            label_id: 标签ID
            
        Returns:
            Dict[str, Any]: 标签定义
        """
        return LabelMapping.get_label_by_id(label_id)
    
    def get_categories(self) -> Dict[str, str]:
        """
        获取所有分类定义
        
        Returns:
            Dict[str, str]: 分类ID到名称的映射
        """
        return LabelMapping.get_categories()
    
    def get_label_mapping_info(self) -> Dict[str, Any]:
        """
        获取标签映射的统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return LabelMapping.get_label_mapping_info()
    
    def get_calculator_info(self) -> Dict[str, str]:
        """
        获取所有计算器的信息
        
        Returns:
            Dict[str, str]: 分类到类名的映射
        """
        return self.registry.get_calculator_info()
    
    def get_available_categories(self) -> List[str]:
        """
        获取所有可用的标签分类
        
        Returns:
            List[str]: 分类列表
        """
        return self.registry.get_all_categories()
    
    def validate_label_id(self, label_id: str) -> bool:
        """
        验证标签ID是否有效
        
        Args:
            label_id: 标签ID
            
        Returns:
            bool: 是否有效
        """
        return LabelMapping.validate_label_id(label_id)
    
    def clear_all_caches(self):
        """清空所有计算器缓存"""
        for calculator in self._calculator_instances.values():
            calculator.clear_cache()
        logger.info("已清空所有标签计算器缓存")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取所有计算器的缓存统计
        
        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        stats = {}
        for category, calculator in self._calculator_instances.items():
            stats[category] = calculator.get_cache_stats()
        return stats
    
    # ============ 配置管理接口 ============
    
    def get_update_frequency(self, label_category: str) -> UpdateFrequency:
        """
        获取标签分类的更新频率
        
        Args:
            label_category: 标签分类
            
        Returns:
            UpdateFrequency: 更新频率
        """
        return LabelConfig.get_update_frequency(label_category)
    
    def get_calculation_params(self, label_category: str) -> Dict[str, Any]:
        """
        获取标签分类的计算参数
        
        Args:
            label_category: 标签分类
            
        Returns:
            Dict[str, Any]: 计算参数
        """
        return LabelConfig.get_calculation_params(label_category)
    
    def get_priority(self, label_category: str) -> int:
        """
        获取标签分类的优先级
        
        Args:
            label_category: 标签分类
            
        Returns:
            int: 优先级
        """
        return LabelConfig.get_priority(label_category)
    
    def get_dependencies(self, label_category: str) -> list:
        """
        获取标签分类的依赖关系
        
        Args:
            label_category: 标签分类
            
        Returns:
            list: 依赖的标签分类列表
        """
        return LabelConfig.get_dependencies(label_category)
    
    def get_timeout(self, label_category: str) -> int:
        """
        获取标签分类的计算超时时间
        
        Args:
            label_category: 标签分类
            
        Returns:
            int: 超时时间（秒）
        """
        return LabelConfig.get_timeout(label_category)
    
    def get_categories_by_frequency(self, frequency: UpdateFrequency) -> list:
        """
        根据更新频率获取标签分类列表
        
        Args:
            frequency: 更新频率
            
        Returns:
            list: 该频率下的标签分类列表
        """
        return LabelConfig.get_categories_by_frequency(frequency)
    
    def get_sorted_categories_by_priority(self) -> list:
        """
        按优先级排序的标签分类列表
        
        Returns:
            list: 按优先级排序的标签分类列表
        """
        return LabelConfig.get_sorted_categories_by_priority()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要信息
        
        Returns:
            Dict[str, Any]: 配置摘要
        """
        return LabelConfig.get_config_summary()