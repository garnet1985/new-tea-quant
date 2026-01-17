#!/usr/bin/env python3
"""
Strategy Manager - 策略管理器（重构精简版）

职责：
- 管理策略生命周期
- 协调各个 helper 完成任务
- 管理全局缓存

代码从 949 行精简到 ~350 行
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Helper 组件
from core.modules.strategy.helper import (
    StrategyDiscoveryHelper,
    StockSamplingHelper,
    JobBuilderHelper,
    StatisticsHelper
)

logger = logging.getLogger(__name__)


class StrategyManager:
    """策略管理器（主进程）"""
    
    def __init__(self, is_verbose: bool = False):
        """初始化策略管理器"""
        self.is_verbose = is_verbose
        
        # 策略缓存
        self.strategy_cache = {}
        
        # 全局缓存
        self.global_cache = {
            'stock_list': None,
            'trading_dates': None,
            'macro_data': None
        }
        
        # 数据管理器
        from core.modules.data_manager import DataManager
        self.data_mgr = DataManager(is_verbose=False)
        
        # 发现所有策略（使用 Helper）
        self.strategy_cache = StrategyDiscoveryHelper.discover_strategies()
    
    # =========================================================================
    # Scanner 执行
    # =========================================================================
    
    def scan(self, strategy_name: str = None, date: str = None):
        """
        执行扫描（Scanner 模式）
        
        Args:
            strategy_name: 策略名称（None = 扫描所有 enabled 策略）
            date: 扫描日期（默认今天）
        """
        # 1. 确定扫描日期
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        # 2. 加载全局缓存
        self._load_global_cache()
        
        # 3. 确定要扫描的策略
        if strategy_name:
            strategies_to_scan = [strategy_name]
        else:
            strategies_to_scan = [
                name for name, info in self.strategy_cache.items()
                if info['settings'].is_enabled
            ]
            
            if not strategies_to_scan:
                logger.warning("没有启用的策略可扫描")
                return
            
            logger.info(f"🔍 扫描所有启用的策略: {strategies_to_scan}")
        
        # 4. 对每个策略执行扫描
        for strat_name in strategies_to_scan:
            self._scan_single_strategy(strat_name, date)
    
    def _scan_single_strategy(self, strategy_name: str, date: str):
        """扫描单个策略"""
        logger.info(f"🔍 开始扫描策略: {strategy_name}")
        
        # 1. 获取策略信息
        strategy_info = self.strategy_cache.get(strategy_name)
        if not strategy_info:
            logger.error(f"策略不存在: {strategy_name}")
            return
        
        settings = strategy_info['settings']
        
        # 2. 获取股票列表（使用 StockSamplingHelper）
        all_stocks = self.global_cache['stock_list']
        stock_list = StockSamplingHelper.get_stock_list(
            all_stocks, 
            settings.sampling_amount,
            settings.sampling_config
        )
        logger.info(f"📊 股票数量: {len(stock_list)}")
        
        # 3. 构建作业（使用 JobBuilderHelper）
        jobs = JobBuilderHelper.build_scan_jobs(stock_list, strategy_info, date)
        logger.info(f"📦 作业数量: {len(jobs)}")
        
        # 4. 多进程执行
        max_workers = self._get_max_workers()
        results = self._execute_jobs(jobs, strategy_info, max_workers)
        
        # 5. 收集结果
        opportunities = self._collect_scan_results(results)
        logger.info(f"✨ 发现机会: {len(opportunities)}")
        
        # 6. 保存结果
        self._save_scan_results(strategy_name, date, opportunities, settings)
        
        logger.info(f"✅ 扫描完成: {strategy_name}")
    
    # =========================================================================
    # Simulator 执行
    # =========================================================================
    
    def simulate(self, strategy_name: str = None, session_id: str = None, date: str = None):
        """
        执行模拟（Simulator 模式）
        
        Args:
            strategy_name: 策略名称（None = 模拟所有 enabled 策略）
            session_id: Session ID（自动生成）
            date: 要回测的扫描日期（默认 latest）
        """
        # 1. 加载全局缓存
        self._load_global_cache()
        
        # 2. 确定要模拟的策略
        if strategy_name:
            strategies_to_simulate = [strategy_name]
        else:
            strategies_to_simulate = [
                name for name, info in self.strategy_cache.items()
                if info['settings'].is_enabled
            ]
            
            if not strategies_to_simulate:
                logger.warning("没有启用的策略可模拟")
                return
            
            logger.info(f"🎮 模拟所有启用的策略: {strategies_to_simulate}")
        
        # 3. 对每个策略执行模拟
        for strat_name in strategies_to_simulate:
            self._simulate_single_strategy(strat_name, session_id, date)
    
    def _simulate_single_strategy(self, strategy_name: str, session_id: str = None, date: str = None):
        """
        模拟单个策略（历史回测）
        
        流程：
        1. 获取股票列表（通过采样策略）
        2. 对每只股票在历史数据上逐日回测
        3. 每天调用用户的 scan_opportunity()
        4. 追踪投资状态（止盈止损）
        5. 返回所有已完成的 opportunities
        """
        logger.info(f"🎮 开始模拟策略: {strategy_name}")
        
        # 1. 获取策略信息
        strategy_info = self.strategy_cache.get(strategy_name)
        if not strategy_info:
            logger.error(f"策略不存在: {strategy_name}")
            return
        
        settings = strategy_info['settings']
        
        # 2. 获取股票列表（使用 StockSamplingHelper）
        stock_list = StockSamplingHelper.get_stock_list(
            global_stock_list=self.global_cache['stock_list'],
            sampling_config=settings.sampling_config,
            data_mgr=self.data_mgr
        )
        logger.info(f"📊 股票数量: {len(stock_list)}")
        
        if not stock_list:
            logger.warning("没有股票可模拟")
            return
        
        # 3. 创建 session
        if session_id is None:
            from core.modules.strategy.components.session_manager import SessionManager
            session_mgr = SessionManager(strategy_name)
            session_id = session_mgr.create_session()
        
        logger.info(f"📝 Session ID: {session_id}")
        
        # 4. 确定回测日期范围
        simulator_config = settings.simulator
        start_date = simulator_config.get('start_date', '20200101')
        end_date = simulator_config.get('end_date', datetime.now().strftime('%Y%m%d'))
        
        logger.info(f"📅 回测日期范围: {start_date} ~ {end_date}")
        
        # 5. 构建作业（使用 JobBuilderHelper）
        jobs = JobBuilderHelper.build_simulate_jobs(
            stock_list, strategy_info, session_id, start_date, end_date
        )
        logger.info(f"📦 作业数量: {len(jobs)}")
        
        # 6. 多进程执行
        max_workers = self._get_max_workers(settings.max_workers)
        results = self._execute_jobs(jobs, strategy_info, max_workers)
        
        # 7. 收集结果（所有已完成的 opportunities）
        all_opportunities = self._collect_simulate_results(results)
        logger.info(f"✅ 完成回测: 共发现 {len(all_opportunities)} 个投资机会")
        
        # 8. 保存结果
        self._save_simulate_results(strategy_name, session_id, all_opportunities, settings)
        
        logger.info(f"✅ 模拟完成: {strategy_name}")
    
    # =========================================================================
    # 多进程执行
    # =========================================================================
    
    def _execute_jobs(
        self, 
        jobs: List[Dict[str, Any]], 
        strategy_info: Dict[str, Any],
        max_workers: int
    ) -> List[Dict[str, Any]]:
        """多进程执行作业"""
        from core.infra.worker.multi_process.process_worker import ExecutionMode as ProcessExecutionMode, ProcessWorker
        
        # 创建 ProcessWorker
        worker_pool = ProcessWorker(
            max_workers=max_workers,
            execution_mode=ProcessExecutionMode.QUEUE,
            job_executor=StrategyManager._execute_single_job,
            is_verbose=self.is_verbose
        )
        
        # 构建 ProcessWorker 格式的 jobs
        process_jobs = [{'id': job['stock_id'], 'payload': job} for job in jobs]
        
        # 执行作业
        worker_pool.run_jobs(process_jobs)
        
        # 获取结果
        job_results = worker_pool.get_results()
        
        # 转换结果格式
        results = []
        for job_result in job_results:
            if job_result.status.value == 'completed':
                results.append(job_result.result)
            else:
                results.append({
                    'success': False,
                    'stock_id': job_result.job_id,
                    'error': str(job_result.error) if job_result.error else 'unknown_error'
                })
        
        return results
    
    @staticmethod
    def _execute_single_job(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Worker 包装函数（在子进程中调用）"""
        import importlib
        
        stock_id = payload.get('stock_id', 'unknown')
        
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
            import traceback
            logger.error(f"Worker 执行失败: stock={stock_id}, error={e}")
            logger.error(f"Details: {traceback.format_exc()}")
            
            return {
                'success': False,
                'stock_id': stock_id,
                'opportunity': None,
                'error': str(e)
            }
    
    # =========================================================================
    # 结果处理
    # =========================================================================
    
    def _collect_scan_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """收集扫描结果"""
        return [r.get('opportunity') for r in results if r.get('success') and r.get('opportunity')]
    
    def _collect_simulate_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        收集模拟结果
        
        注意：每个 result 包含 'settled' 列表（一只股票可能有多个 opportunities）
        
        Returns:
            所有 opportunities 的扁平列表
        """
        all_opportunities = []
        for r in results:
            if r.get('success'):
                settled = r.get('settled', [])
                all_opportunities.extend(settled)
        return all_opportunities
    
    def _save_scan_results(
        self, 
        strategy_name: str, 
        date: str, 
        opportunities: List[Dict[str, Any]],
        settings: Any
    ):
        """保存扫描结果"""
        from core.modules.strategy.components.opportunity_service import OpportunityService
        
        opp_service = OpportunityService(strategy_name)
        
        # 1. 保存配置
        opp_service.save_scan_config(date, settings.to_dict())
        
        # 2. 保存机会
        grouped = {}
        for opp in opportunities:
            stock_id = opp['stock_id']
            if stock_id not in grouped:
                grouped[stock_id] = []
            grouped[stock_id].append(opp)
        
        for stock_id, opps in grouped.items():
            opp_service.save_scan_opportunities(date, stock_id, opps)
        
        # 3. 保存 summary（使用 StatisticsHelper）
        strategy_version = settings.name
        summary = StatisticsHelper.generate_scan_summary(
            strategy_name, date, strategy_version, len(opportunities), opportunities
        )
        opp_service.save_scan_summary(date, summary)
    
    def _save_simulate_results(
        self,
        strategy_name: str,
        session_id: str,
        opportunities: List[Dict[str, Any]],
        settings: Any
    ):
        """保存模拟结果"""
        from core.modules.strategy.components.opportunity_service import OpportunityService
        
        opp_service = OpportunityService(strategy_name)
        
        # 1. 保存配置
        opp_service.save_simulate_config(session_id, settings.to_dict())
        
        # 2. 保存机会
        grouped = {}
        for opp in opportunities:
            stock_id = opp['stock_id']
            if stock_id not in grouped:
                grouped[stock_id] = []
            grouped[stock_id].append(opp)
        
        for stock_id, opps in grouped.items():
            opp_service.save_simulate_opportunities(session_id, stock_id, opps)
        
        # 3. 保存 summary（使用 StatisticsHelper）
        summary = StatisticsHelper.generate_simulate_summary(
            strategy_name, session_id, opportunities
        )
        opp_service.save_simulate_summary(session_id, summary)
    
    # =========================================================================
    # 辅助方法
    # =========================================================================
    
    def _get_max_workers(self, config_value: Any = None) -> int:
        """获取最大进程数"""
        import os
        
        if config_value is None or config_value == 'auto':
            cpu_count = os.cpu_count() or 4
            return max(1, cpu_count - 1)
        
        try:
            return int(config_value)
        except (ValueError, TypeError):
            return 4
    
    def _load_global_cache(self):
        """加载全局缓存"""
        if self.global_cache['stock_list'] is None:
            try:
                stock_list = self.data_mgr.stock.list.load_filtered()
                self.global_cache['stock_list'] = stock_list
                logger.info(f"📊 加载股票列表: {len(stock_list)} 只")
            except Exception as e:
                logger.error(f"加载股票列表失败: {e}")
                self.global_cache['stock_list'] = []
    
    def list_strategies(self) -> List[str]:
        """列出所有已发现的策略"""
        return list(self.strategy_cache.keys())
    
    def get_strategy_info(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """获取策略信息"""
        return self.strategy_cache.get(strategy_name)


# =========================================================================
# CLI 入口
# =========================================================================

if __name__ == "__main__":
    import sys
    
    # 用法: python strategy_manager.py <scan|simulate> [strategy_name]
    
    if len(sys.argv) < 2:
        print("用法: python strategy_manager.py <scan|simulate> [strategy_name]")
        sys.exit(1)
    
    mode = sys.argv[1]
    strategy_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    manager = StrategyManager(is_verbose=True)
    
    if mode == 'scan':
        manager.scan(strategy_name)
    elif mode == 'simulate':
        manager.simulate(strategy_name)
    else:
        print(f"未知模式: {mode}")
