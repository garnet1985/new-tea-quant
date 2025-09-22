#!/usr/bin/env python3
"""
Simulator 核心类 - 提供统一的策略模拟接口
"""
import time
from typing import Dict, List, Any, Optional, Callable
from loguru import logger
from .services.simulating_service import SimulatingService
from .services.preprocess_service import PreprocessService
from .services.postprocess_service import PostprocessService
from utils.icon.icon_service import IconService


class Simulator:
    def __init__(self):
        pass

    def run(self, settings: Dict[str, Any], module_info: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()
        
        stock_list = self.preprocess(settings, module_info)
        simulate_result = self.simulating(stock_list, module_info, settings)
        # report = self.postprocess(on_single_stock_summary, on_session_summary, on_simulate_complete, simulate_result, settings)
        
        total_time = time.time() - start_time
        logger.info(f"{IconService.get('success')} 模拟流程完成！总耗时: {total_time:.2f}秒")
        # return report
    
    def preprocess(self, settings: Dict[str, Any], module_info: Optional[Callable] = None) -> List[Dict[str, Any]]:

        stock_list = PreprocessService.preprocess(settings)

        import importlib
        strategy_module = importlib.import_module(module_info.get('strategy_module_path', ''))
        strategy_class = getattr(strategy_module, module_info.get('strategy_class_name', ''))

        stock_list = strategy_class.on_before_simulate(stock_list, settings)
        
        return stock_list

    
    def simulating(self, stock_list: List[Dict[str, Any]], module_info: Dict[str, Any], settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        jobs = SimulatingService.build_jobs(stock_list, module_info, settings)
        # 使用多进程执行
        simulate_results = SimulatingService.run_multiprocess_simulation(jobs, module_info)
        return simulate_results


    def postprocess(self, on_single_stock_summary: Optional[Callable] = None,
                    on_session_summary: Optional[Callable] = None,
                    on_simulate_complete: Optional[Callable] = None,
                    simulate_results: List[Dict[str, Any]] = None,
                    settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        后处理阶段 - 汇总和生成报告
        
        Args:
            on_single_stock_summary: 单股票汇总回调函数
            on_session_summary: 会话汇总回调函数
            on_simulate_complete: 完成回调函数
            simulate_results: 模拟结果列表
            
        Returns:
            Dict: 最终报告
        """
        start_time = time.time()
        
        # 获取模拟结果
        if not simulate_results:
            logger.warning(f"{IconService.get('warning')} 没有模拟结果需要处理")
            return {}
        
        # 步骤1：单股票汇总
        stock_summaries = PostprocessService.summarize_stocks(simulate_results, on_single_stock_summary)
        
        # 步骤2：会话汇总
        session_summary = PostprocessService.summarize_session(stock_summaries, on_session_summary)
        
        # 步骤3：生成最终报告
        final_report = PostprocessService.generate_quick_simulate_report(
            simulate_results=simulate_results,
            stock_summaries=stock_summaries,
            session_summary=session_summary,
            settings=settings or {},
            processing_time=time.time() - start_time,
            on_simulate_complete=on_simulate_complete
        )

        PostprocessService.log_quick_simulate_report(final_report)
        
        return final_report
