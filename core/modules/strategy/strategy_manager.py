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
from core.modules.strategy.helpers import (
    StrategyDiscoveryHelper,
    StockSamplingHelper,
    JobBuilderHelper,
    StatisticsHelper,
)
from core.modules.strategy.data_classes.strategy_info import StrategyInfo
from core.modules.strategy.data_classes.strategy_settings.strategy_settings import (
    StrategySettings,
)

logger = logging.getLogger(__name__)


class StrategyManager:
    """策略管理器（主进程）"""
    
    def __init__(self, is_verbose: bool = False):
        """初始化策略管理器"""
        self.is_verbose = is_verbose
        
        # 全局缓存（按需写入；如 stock_list 由 _load_stock_list 填充）
        self.global_cache: Dict[str, Any] = {}
        
        # 数据管理器
        from core.modules.data_manager import DataManager
        self.data_mgr = DataManager(is_verbose=False)
        
        # 发现阶段已做 settings.validate()；只保留一份「校验通过」映射，是否启用看 ``StrategyInfo.is_enabled``
        self.validated_strategies = StrategyDiscoveryHelper.discover_strategies()

    def lookup_strategy_info(self, strategy_name: str) -> Optional[StrategyInfo]:
        """
        按名称解析 ``StrategyInfo``：先查 ``validated_strategies``，未命中再对该目录 ``load_strategy``。
        供 CLI / 其它模块及本类内部共用。
        """
        info = self.validated_strategies.get(strategy_name)
        if info is not None:
            return info
        from core.infra.project_context import PathManager

        folder = PathManager.userspace() / "strategies" / strategy_name
        if not folder.is_dir():
            return None
        return StrategyDiscoveryHelper.load_strategy(folder)
    
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
        
        self._load_stock_list()

        # 3. 确定要扫描的策略（仅 is_enabled；settings 已在发现时校验）
        if strategy_name:
            strategy_info = self.lookup_strategy_info(strategy_name)
            if not strategy_info:
                logger.warning(f"策略不存在或未发现: {strategy_name}")
                return
            if not strategy_info.is_enabled:
                logger.warning(f"策略未启用: {strategy_name}")
                return
            to_run = [strategy_info]
        else:
            to_run = [info for info in self.validated_strategies.values() if info.is_enabled]

        if not to_run:
            logger.warning("没有启用的策略可扫描")
            return

        for strategy_info in to_run:
            self._scan_single_strategy(strategy_info, date)
    
    def _scan_single_strategy(self, strategy_info: StrategyInfo, date: str):
        """扫描单个策略（入参为 ``StrategyInfo``；settings 为 data_classes ``StrategySettings``）。"""
        strategy_name = strategy_info.name
        settings: StrategySettings = strategy_info.settings
        scanner = settings.scanner
        logger.info(f"🔍 开始扫描策略: {strategy_name}")

        all_stocks = self._load_stock_list()

        watch_list = scanner.watch_list
        if watch_list:
            stock_list = StockSamplingHelper.filter_stocks_by_list(
                all_stocks=all_stocks,
                watch_list=watch_list,
                strategy_name=strategy_name,
            )
        else:
            stock_list = [s["id"] for s in all_stocks]
        logger.info(f"📊 股票数量: {len(stock_list)}")
        
        # 3. 构建作业（使用 JobBuilderHelper）
        jobs = JobBuilderHelper.build_scan_jobs(stock_list, strategy_info, date)
        logger.info(f"📦 作业数量: {len(jobs)}")
        
        # 4. 多进程执行（并行度来自 scanner 块，与 settings_example 一致）
        max_workers = self._get_max_workers(scanner.max_workers)
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
        
        # 2. 确定要模拟的策略（内部一律传 ``StrategyInfo``）
        if strategy_name:
            info = self.lookup_strategy_info(strategy_name)
            if not info:
                logger.warning(f"策略不存在或设置无效: {strategy_name}")
                return
            to_simulate = [info]
        else:
            to_simulate = [i for i in self.validated_strategies.values() if i.is_enabled]
            if not to_simulate:
                logger.warning("没有启用的策略可模拟")
                return
            logger.info(
                "🎮 模拟所有启用的策略: %s",
                [i.name for i in to_simulate],
            )
        
        # 3. 对每个策略执行模拟
        for info in to_simulate:
            self._simulate_single_strategy(info, session_id, date)
    
    def _simulate_single_strategy(
        self, strategy_info: StrategyInfo, session_id: str = None, date: str = None
    ):
        """
        模拟单个策略（历史回测）
        
        流程：
        1. 获取股票列表（通过采样策略）
        2. 对每只股票在历史数据上逐日回测
        3. 每天调用用户的 scan_opportunity()
        4. 追踪投资状态（止盈止损）
        5. 返回所有已完成的 opportunities
        """
        name = strategy_info.name
        logger.info(f"🎮 开始模拟策略: {name}")
        strategy_settings: StrategySettings = strategy_info.settings
        price_block = strategy_settings.price_simulator
        sampling_block = strategy_settings.sampling
        
        # 2. 获取股票列表
        # 规则与 price_simulator 对齐：
        # - price_simulator.use_sampling = True  -> 使用 sampling 配置
        # - price_simulator.use_sampling = False -> 使用全量股票
        all_stocks = self._load_stock_list()

        price_simulator_config = price_block.price_simulator
        is_use_sampling = bool(price_simulator_config.get("use_sampling", True))
        
        if is_use_sampling:
            sampling_cfg = sampling_block.sampling
            sampling_amount = sampling_block.get_sampling_amount() or len(all_stocks)
            stock_list = StockSamplingHelper.get_stock_list(
                all_stocks=all_stocks,
                sampling_amount=sampling_amount,
                sampling_config=sampling_cfg,
                strategy_name=name,
            )
            logger.info("🧪 模拟股票模式: sampling (use_sampling=True)")
        else:
            stock_list = [s["id"] for s in all_stocks]
            logger.info("📦 模拟股票模式: full (use_sampling=False)")
        logger.info(f"📊 股票数量: {len(stock_list)}")
        
        if not stock_list:
            logger.warning("没有股票可模拟")
            return
        
        # 3. 创建 session
        if session_id is None:
            from core.modules.strategy.components.session_manager import SessionManager
            session_mgr = SessionManager(name)
            session_id = session_mgr.create_session()
        
        logger.info(f"📝 Session ID: {session_id}")
        
        # 4. 确定回测日期范围
        simulator_config = price_simulator_config
        start_date = simulator_config.get('start_date') or '20200101'
        end_date = simulator_config.get('end_date') or datetime.now().strftime('%Y%m%d')
        
        logger.info(f"📅 回测日期范围: {start_date} ~ {end_date}")
        
        # 5. 构建作业（使用 JobBuilderHelper）
        jobs = JobBuilderHelper.build_simulate_jobs(
            stock_list, strategy_info, session_id, start_date, end_date
        )
        logger.info(f"📦 作业数量: {len(jobs)}")
        
        # 6. 多进程执行（与 PriceFactorSimulator / price_simulator 块一致）
        max_workers = self._get_max_workers(price_block.max_workers)
        results = self._execute_jobs(jobs, strategy_info, max_workers)
        
        # 7. 收集结果（所有已完成的 opportunities）
        all_opportunities = self._collect_simulate_results(results)
        logger.info(f"✅ 完成回测: 共发现 {len(all_opportunities)} 个投资机会")
        
        # 8. 保存结果
        self._save_simulate_results(name, session_id, all_opportunities, strategy_settings)
        
        logger.info(f"✅ 模拟完成: {name}")
    
    # =========================================================================
    # 多进程执行
    # =========================================================================
    
    def _execute_jobs(
        self, 
        jobs: List[Dict[str, Any]], 
        strategy_info: Any,
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
        settings: StrategySettings,
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
        strategy_version = settings.strategy_name
        summary = StatisticsHelper.generate_scan_summary(
            strategy_name, date, strategy_version, len(opportunities), opportunities
        )
        opp_service.save_scan_summary(date, summary)
    
    def _save_simulate_results(
        self,
        strategy_name: str,
        session_id: str,
        opportunities: List[Dict[str, Any]],
        settings: StrategySettings,
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
        self._load_stock_list()
    
    def list_strategies(self) -> List[str]:
        """列出所有已发现且 settings 校验通过的策略名称（含未启用；筛启用请用 ``info.is_enabled``）。"""
        return list(self.validated_strategies.keys())
    
    def get_strategy_info(self, strategy_name: str) -> Optional[StrategyInfo]:
        """返回策略信息（同 ``lookup_strategy_info``）。"""
        return self.lookup_strategy_info(strategy_name)

# ================================================
# Cache 缓存相关（跨多个strategy的缓存，也叫globa cache）
# ================================================

    def _load_stock_list(self) -> List[Dict[str, Any]]:
        stock_list = self.get_global_cache('stock_list')
        if not stock_list:
            stock_list = self.data_mgr.stock.list.load_filtered()
            self.set_global_cache('stock_list', stock_list)
        return stock_list

    def set_global_cache(self, key: str, value: Any):
        """设置全局缓存"""
        self.global_cache[key] = value
    
    def get_global_cache(self, key: str) -> Any:
        """获取全局缓存"""
        return self.global_cache.get(key)
    
    def clear_global_cache(self):
        """清空全局缓存"""
        self.global_cache.clear()

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
