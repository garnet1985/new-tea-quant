#!/usr/bin/env python3
"""
Scanner - 扫描器主类

职责：
- 整合所有组件（日期解析、缓存、adapter）
- 多进程扫描
- 汇总结果并分发
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import logging
import time
from pathlib import Path

from core.modules.strategy.enums import ExecutionMode
from core.modules.strategy.components.scanner.scan_date_resolver import ScanDateResolver
from core.modules.strategy.components.scanner.scan_cache_manager import ScanCacheManager
from core.modules.strategy.components.scanner.adapter_dispatcher import AdapterDispatcher
from core.modules.strategy.components.setting_management.models.scanner_settings import ScannerSettings
from core.modules.strategy.models.opportunity import Opportunity

logger = logging.getLogger(__name__)


@dataclass
class Scanner:
    """扫描器主类"""
    
    strategy_name: str
    data_manager: any  # DataManager 实例
    is_verbose: bool = False
    
    def __post_init__(self):
        """初始化组件"""
        # 加载配置
        self.settings = ScannerSettings.load_from_strategy_name(self.strategy_name)
        self.settings.validate_and_prepare()
        
        # 初始化组件
        self.date_resolver = ScanDateResolver(self.data_manager)
        self.cache_manager = ScanCacheManager(
            strategy_name=self.strategy_name,
            max_cache_days=self.settings.max_cache_days
        )
        self.adapter_dispatcher = AdapterDispatcher(self.strategy_name)
    
    def scan(self) -> Dict[str, Any]:
        """
        执行扫描
        
        Returns:
            {
                'date': 扫描日期,
                'total_opportunities': 总机会数,
                'total_stocks': 扫描股票数,
                'summary': {...}
            }
        """
        # 记录开始时间
        start_time = time.time()
        
        logger.info(f"🚀 [Scanner] 开始扫描: strategy={self.strategy_name}")
        
        # 1. 解析日期和股票列表
        scan_date, stock_ids = self.date_resolver.resolve_scan_date(
            use_strict=self.settings.use_strict_previous_trading_day
        )
        
        logger.info(
            f"[Scanner] 扫描日期: {scan_date}, "
            f"股票数量: {len(stock_ids)}"
        )
        
        # 2. 清理旧缓存
        self.cache_manager.cleanup_old_cache()
        
        # 3. 多进程扫描
        opportunities = self._scan_stocks(scan_date, stock_ids)
        
        # 4. 保存缓存
        if opportunities:
            self.cache_manager.save_opportunities(scan_date, opportunities)
        
        # 5. 汇总统计
        summary = self._calculate_summary(opportunities)
        
        # 6. 调用 Adapters（支持多个）
        context = {
            'date': scan_date,
            'strategy_name': self.strategy_name,
            'scan_summary': summary
        }
        self.adapter_dispatcher.dispatch(
            adapter_names=self.settings.adapter_names,
            opportunities=opportunities,
            context=context
        )
        
        # 7. 返回结果（总时长已在上面记录）
        result = {
            'date': scan_date,
            'total_opportunities': len(opportunities),
            'total_stocks': len(stock_ids),
            'summary': summary
        }
        
        logger.info(
            f"[Scanner] 扫描完成: "
            f"日期={scan_date}, "
            f"机会数={len(opportunities)}, "
            f"股票数={len(stock_ids)}"
        )
        
        return result
    
    def _scan_stocks(
        self,
        scan_date: str,
        stock_ids: List[str]
    ) -> List[Opportunity]:
        """
        多进程扫描股票
        
        Args:
            scan_date: 扫描日期
            stock_ids: 股票 ID 列表
        
        Returns:
            机会列表
        """
        from core.infra.worker.multi_process.process_worker import (
            ProcessWorker,
            ExecutionMode as ProcessExecutionMode,
        )
        
        # 获取 worker 信息（用于子进程加载）
        worker_module_path = f"userspace.strategies.{self.strategy_name}.strategy_worker"
        worker_class_name = self._get_worker_class_name()
        
        # 构建 job list
        jobs = []
        for stock_id in stock_ids:
            jobs.append({
                'stock_id': stock_id,
                'execution_mode': ExecutionMode.SCAN.value,
                'strategy_name': self.strategy_name,
                'settings': self.settings.to_dict(),
                'scan_date': scan_date,
                'worker_module_path': worker_module_path,
                'worker_class_name': worker_class_name
            })
        
        # 解析 max_workers
        resolved_workers = ProcessWorker.resolve_max_workers(
            self.settings.max_workers,
            module_name="Scanner"
        )
        
        # 创建 ProcessWorker
        worker_pool = ProcessWorker(
            max_workers=resolved_workers,
            execution_mode=ProcessExecutionMode.QUEUE,
            job_executor=Scanner._execute_single_job,
            is_verbose=self.is_verbose
        )
        
        # 构建 ProcessWorker 格式的 jobs
        process_jobs = [{'id': job['stock_id'], 'payload': job} for job in jobs]
        
        # 执行作业（ProcessWorker 内部会显示进度）
        worker_pool.run_jobs(process_jobs)
        
        # 获取结果和统计信息
        job_results = worker_pool.get_results()
        stats = worker_pool.stats
        
        # 计算总时长
        total_elapsed = time.time() - start_time
        if total_elapsed < 60:
            total_time_str = f"{total_elapsed:.1f}秒"
        elif total_elapsed < 3600:
            total_time_str = f"{total_elapsed/60:.1f}分钟"
        else:
            hours = int(total_elapsed // 3600)
            minutes = int((total_elapsed % 3600) // 60)
            total_time_str = f"{hours}小时{minutes}分钟"
        
        logger.info(
            f"✅ [Scanner] 扫描完成: 成功={stats.get('completed_jobs', 0)}, "
            f"失败={stats.get('failed_jobs', 0)}, 总耗时={total_time_str}"
        )
        
        # 收集所有机会
        opportunities = []
        for job_result in job_results:
            if job_result.status.value == 'completed':
                result = job_result.result
                if result.get('success') and result.get('opportunity'):
                    # 转换为 Opportunity dataclass
                    opp_dict = result['opportunity']
                    opp = Opportunity.from_dict(opp_dict)
                    opportunities.append(opp)
        
        return opportunities
    
    def _get_worker_class_name(self) -> str:
        """获取 Worker 类名"""
        import importlib
        import inspect
        from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
        
        module_path = f"userspace.strategies.{self.strategy_name}.strategy_worker"
        try:
            module = importlib.import_module(module_path)
            
            # 查找继承自 BaseStrategyWorker 的类
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, BaseStrategyWorker)
                    and obj is not BaseStrategyWorker
                ):
                    return obj.__name__
            
            # 如果找不到，返回默认名称
            return "StrategyWorker"
        except Exception as e:
            logger.warning(f"[Scanner] 无法获取 Worker 类名，使用默认: {e}")
            return "StrategyWorker"
    
    @staticmethod
    def _execute_single_job(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Worker 包装函数（在子进程中调用）
        
        Args:
            payload: {
                'stock_id': '000001.SZ',
                'execution_mode': 'scan',
                'strategy_name': 'example',
                'settings': {...},
                'scan_date': '20250113',
                'worker_module_path': '...',
                'worker_class_name': '...'
            }
        
        Returns:
            {
                'success': True/False,
                'stock_id': '000001.SZ',
                'opportunity': {...} or None,
                'error': '...' (if failed)
            }
        """
        import importlib
        
        stock_id = payload['stock_id']
        
        try:
            # 1. 动态加载 Worker 类
            worker_module_path = payload.get('worker_module_path')
            worker_class_name = payload.get('worker_class_name')
            
            if not worker_module_path or not worker_class_name:
                raise ValueError(f"缺少 worker 信息")
            
            worker_module = importlib.import_module(worker_module_path)
            worker_class = getattr(worker_module, worker_class_name)
            
            # 2. 实例化并运行
            worker = worker_class(payload)
            result = worker.run()
            
            return result
        
        except Exception as e:
            logger.error(
                f"[Scanner] 扫描股票失败: stock_id={stock_id}, error={e}",
                exc_info=True
            )
            return {
                'success': False,
                'stock_id': stock_id,
                'opportunity': None,
                'error': str(e)
            }
    
    def _calculate_summary(
        self,
        opportunities: List[Opportunity]
    ) -> Dict[str, Any]:
        """
        计算扫描汇总统计
        
        Args:
            opportunities: 机会列表
        
        Returns:
            汇总统计字典
        """
        if not opportunities:
            return {
                'total_opportunities': 0,
                'total_stocks': 0,
                'stocks_with_opportunities': set()
            }
        
        stocks_with_opps = set([opp.stock_id for opp in opportunities])
        
        return {
            'total_opportunities': len(opportunities),
            'total_stocks': len(stocks_with_opps),
            'stocks_with_opportunities': list(stocks_with_opps)
        }
