#!/usr/bin/env python3
"""
Simulator 核心类 - 提供统一的策略模拟接口
"""
import time
from typing import Dict, List, Any
from loguru import logger

from app.analyzer.components.investment.investment_recorder import InvestmentRecorder
from .services.simulating_service import SimulatingService
from .services.preprocess_service import PreprocessService
from .services.postprocess_service import PostprocessService
from utils.icon.icon_service import IconService


class Simulator:
    def __init__(self):
        self.invest_recorder = InvestmentRecorder()

    def run(self, module_info: Dict[str, Any]) -> Dict[str, Any]:
        start_time = time.time()

        import importlib
        strategy_module = importlib.import_module(module_info.get('strategy_module_path', ''))
        strategy_class = getattr(strategy_module, module_info.get('strategy_class_name', ''))
        settings = importlib.import_module(module_info.get('strategy_settings_path')).settings

        self.invest_recorder.set_strategy_folder_name(module_info.get('strategy_folder_name', ''))

        stock_list = self.preprocess(settings, strategy_class)

        simulate_results = self.simulating(stock_list, strategy_class, settings)

        # report = self.postprocess(simulate_results, strategy_class, settings, module_info)
        
        
        # total_time = time.time() - start_time
        # logger.info(f"{IconService.get('success')} 模拟流程完成！总耗时: {total_time:.2f}秒")
        
        # return report
    
    
    def preprocess(self, settings: Dict[str, Any], strategy_class: Any) -> List[Dict[str, Any]]:

        stock_list = PreprocessService.get_stock_list(settings)

        stock_list = strategy_class.on_before_simulate(stock_list, settings)
        
        return stock_list

    
    def simulating(self, stock_list: List[Dict[str, Any]], strategy_class: Any, settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        jobs = SimulatingService.build_jobs(stock_list, strategy_class, settings)
        # 使用多进程执行
        simulate_results = SimulatingService.run_multiprocess_simulation(jobs)
        return simulate_results


    def postprocess(self, simulate_results: List[Dict[str, Any]], strategy_class: Any, settings: Dict[str, Any], module_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        后处理阶段 - 汇总和生成报告
        
        Args:
            simulate_results: 模拟结果列表
            module_info: 模块信息
            settings: 设置
            
        Returns:
            Dict: 最终报告
        """
        
        # 获取模拟结果
        if not simulate_results or len(simulate_results) == 0:
            logger.warning(f"{IconService.get('warning')} 没有模拟结果需要处理")
            return {}

        stock_summaries = []

        for simulate_result in simulate_results:
            stock_summary = PostprocessService.summarize_stock(simulate_result, strategy_class)
            # 只保存有投资的股票记录
            if stock_summary.get('summary', {}).get('total_investments', 0) > 0:
                stock_summaries.append(stock_summary)

        session_summary = PostprocessService.summarize_session(stock_summaries, strategy_class, settings)

        self.invest_recorder.save_simulation_results(stock_summaries, session_summary)

        session_summary = strategy_class.on_before_report(session_summary)

        PostprocessService.present_session_report(session_summary, settings, strategy_class().name, module_info)

        return session_summary


