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

    # Args:
    #     settings: 策略设置（包含 simulate_base_term 等）
    #     on_before_simulate: 模拟开始前的回调函数
    #     on_simulate_one_day: 单日模拟函数
    #     on_single_stock_summary: 单股票汇总函数
    #     on_session_summary: 整个会话汇总函数
    #     on_simulate_complete: 模拟完成后的最终回调函数
    
    # Returns:
    #     Dict: 最终报告
    def run(self, settings: Dict[str, Any], 
            on_before_simulate: Optional[Callable] = None, 
            on_simulate_one_day: Optional[Callable] = None,
            on_summarize_stock: Optional[Callable] = None,
            on_summarize_session: Optional[Callable] = None,
            on_before_report: Optional[Callable] = None) -> Dict[str, Any]:
        
        start_time = time.time()
        
        # 执行三个步骤
        stock_list = self.preprocess(settings, on_before_simulate)
        simulate_result = self.simulating(stock_list, settings, on_simulate_one_day)
        # report = self.postprocess(on_single_stock_summary, on_session_summary, on_simulate_complete, simulate_result, settings)
        
        total_time = time.time() - start_time
        logger.info(f"{IconService.get('success')} 模拟流程完成！总耗时: {total_time:.2f}秒")
        # return report
    
    # 预处理阶段 - 验证设置，获取股票列表
    
    # Args:
    #     settings: 策略设置
    #     on_before_simulate: 模拟开始前的回调函数
    #     on_simulate_one_day: 单日模拟函数（用于校验）
        
    # Returns:
    #     tuple: (validated_settings, stock_list)
    def preprocess(self, settings: Dict[str, Any], on_before_simulate: Optional[Callable] = None, 
                   on_simulate_one_day: Optional[Callable] = None) -> tuple:

        # 使用 PreprocessService 进行预处理（包含函数校验）
        stock_list = PreprocessService.preprocess(settings)
        
        if on_before_simulate:
            stock_list = on_before_simulate(stock_list, settings)
        
        # logger.info(f"{IconService.get('success')} 获取股票列表完成: {len(stock_list)} 只股票")

        return stock_list, settings

    
    # 模拟阶段 - 执行单日模拟流程
    
    # Args:
    #     on_simulate_one_day: 单日模拟函数
    
    # Returns:
    #     List[Dict]: 模拟结果列表
    def simulating(self, stock_list: List[Dict[str, Any]], settings: Dict[str, Any], on_simulate_one_day: Optional[Callable] = None) -> List[Dict[str, Any]]:
        # 构建多进程任务 - 传递单日模拟函数
        jobs = SimulatingService.build_simulation_jobs_from_stock_list(
            stock_list, settings, on_simulate_one_day
        )

        logger.info(f"aabbcc构建多进程任务: {len(jobs)} 个任务")
        
        # 使用多进程执行
        simulate_results = SimulatingService.run_multiprocess_simulation(jobs)
        return simulate_results




    # 后处理阶段 - 生成报告和分析
    
    # Args:
    #     on_single_stock_summary: 单股票汇总函数
    #     on_session_summary: 整个会话汇总函数
    #     on_simulate_complete: 模拟完成后的最终回调函数
        
    # Returns:
    #     Dict: 最终报告
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
