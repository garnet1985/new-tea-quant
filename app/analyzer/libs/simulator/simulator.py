#!/usr/bin/env python3
"""
Simulator 核心类 - 提供统一的策略模拟接口
"""
import time
from typing import Dict, List, Any, Optional, Callable
from loguru import logger
from .services.simulating_service import SimulatingService
from .services.preprocess_service import PreprocessService


class Simulator:
    """策略模拟器 - 提供统一的模拟接口"""
    
    def __init__(self):
        """初始化模拟器"""
        self.settings = None
        self.stock_list = None
        self.simulate_result = None
        self.report = None
        
        logger.info("🔧 初始化 Simulator")
    
    def run(self, settings: Dict[str, Any], 
            on_before_simulate: Optional[Callable] = None, 
            on_simulate_one_day: Optional[Callable] = None,
            on_single_stock_summary: Optional[Callable] = None,
            on_session_summary: Optional[Callable] = None,
            on_simulate_complete: Optional[Callable] = None) -> Dict[str, Any]:
        """
        一键运行完整的模拟流程
        
        Args:
            settings: 策略设置（包含 simulate_base_term 等）
            on_before_simulate: 模拟开始前的回调函数
            on_simulate_one_day: 单日模拟函数
            on_single_stock_summary: 单股票汇总函数
            on_session_summary: 整个会话汇总函数
            on_simulate_complete: 模拟完成后的最终回调函数
        
        Returns:
            Dict: 最终报告
        """
        start_time = time.time()
        logger.info("🚀 开始完整模拟流程...")
        
        # 重置状态
        self.reset()
        
        # 执行三个步骤
        self.settings, self.stock_list = self.preprocess(settings, on_before_simulate, on_simulate_one_day)
        self.simulate_result = self.simulating(on_simulate_one_day)
        self.report = self.postprocess(on_single_stock_summary, on_session_summary, on_simulate_complete)
        
        total_time = time.time() - start_time
        logger.info(f"🎉 完整模拟流程完成！总耗时: {total_time:.2f}秒")
        return self.report
    
    def reset(self):
        """重置模拟器状态"""
        self.settings = None
        self.stock_list = None
        self.simulate_result = None
        self.report = None
    
    def preprocess(self, settings: Dict[str, Any], on_before_simulate: Optional[Callable] = None, 
                   on_simulate_one_day: Optional[Callable] = None) -> tuple:
        """
        预处理阶段 - 验证设置，获取股票列表
        
        Args:
            settings: 策略设置
            on_before_simulate: 模拟开始前的回调函数
            on_simulate_one_day: 单日模拟函数（用于校验）
            
        Returns:
            tuple: (validated_settings, stock_list)
        """
        start_time = time.time()
        logger.info("📋 开始预处理阶段...")
        
        # 使用 PreprocessService 进行预处理（包含函数校验）
        validated_settings, stock_list = PreprocessService.preprocess(settings, on_simulate_one_day)
        
        if on_before_simulate:
            on_before_simulate(validated_settings, stock_list)
        
        elapsed_time = time.time() - start_time
        logger.info(f"✅ 预处理完成，耗时: {elapsed_time:.2f}秒")
        return validated_settings, stock_list
    
    def simulating(self, on_simulate_one_day: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        模拟阶段 - 执行单日模拟流程
        
        Args:
            on_simulate_one_day: 单日模拟函数
        
        Returns:
            List[Dict]: 模拟结果列表
        """
        start_time = time.time()
        logger.info("🔍 开始模拟阶段...")
        
        # 获取股票列表和设置
        stock_list = self.stock_list
        settings = self.settings
        
        # 构建多进程任务 - 传递单日模拟函数
        jobs = SimulatingService.build_simulation_jobs_from_stock_list(
            stock_list, settings, on_simulate_one_day
        )
        
        # 使用多进程执行
        simulate_results = SimulatingService.run_multiprocess_simulation(jobs)
        
        elapsed_time = time.time() - start_time
        logger.info(f"✅ 模拟完成: {len(simulate_results)} 只股票的模拟结果，耗时: {elapsed_time:.2f}秒")
        return simulate_results
    
    def postprocess(self, on_single_stock_summary: Optional[Callable] = None,
                    on_session_summary: Optional[Callable] = None,
                    on_simulate_complete: Optional[Callable] = None) -> Dict[str, Any]:
        """
        后处理阶段 - 生成报告和分析
        
        Args:
            on_single_stock_summary: 单股票汇总函数
            on_session_summary: 整个会话汇总函数
            on_simulate_complete: 模拟完成后的最终回调函数
            
        Returns:
            Dict: 最终报告
        """
        start_time = time.time()
        logger.info("📊 开始后处理阶段...")
        
        # 获取模拟结果
        simulate_results = self.simulate_result
        if not simulate_results:
            logger.warning("⚠️ 没有模拟结果需要处理")
            return {}
        
        # 步骤1：单股票汇总
        stock_summaries = []
        for result in simulate_results:
            stock_id = result.get('stock_id', 'unknown')
            
            # 调用用户自定义的单股票汇总函数
            if on_single_stock_summary:
                try:
                    summary = on_single_stock_summary(result)
                    stock_summaries.append({
                        'stock_id': stock_id,
                        'summary': summary
                    })
                except Exception as e:
                    logger.error(f"❌ 股票 {stock_id} 汇总失败: {e}")
                    stock_summaries.append({
                        'stock_id': stock_id,
                        'summary': None,
                        'error': str(e)
                    })
            else:
                # 默认汇总逻辑
                investments = result.get('investments', [])
                settled_investments = result.get('settled_investments', [])
                stock_summaries.append({
                    'stock_id': stock_id,
                    'summary': {
                        'total_investments': len(investments),
                        'total_settled': len(settled_investments),
                        'current_investments': len(investments)
                    }
                })
        
        # 步骤2：整个会话汇总
        session_summary = None
        if on_session_summary:
            try:
                session_summary = on_session_summary(stock_summaries)
            except Exception as e:
                logger.error(f"❌ 会话汇总失败: {e}")
                session_summary = {'error': str(e)}
        else:
            # 默认会话汇总逻辑
            total_stocks = len(stock_summaries)
            total_investments = sum(s.get('summary', {}).get('total_investments', 0) for s in stock_summaries)
            total_settled = sum(s.get('summary', {}).get('total_settled', 0) for s in stock_summaries)
            
            session_summary = {
                'total_stocks': total_stocks,
                'total_investments': total_investments,
                'total_settled': total_settled,
                'success_rate': total_settled / total_investments if total_investments > 0 else 0
            }
        
        # 构建最终报告
        final_report = {
            'session_summary': session_summary,
            'stock_summaries': stock_summaries,
            'raw_results': simulate_results,
            'settings': self.settings,
            'processing_time': time.time() - start_time
        }
        
        # 步骤3：最终回调
        if on_simulate_complete:
            try:
                on_simulate_complete(final_report)
            except Exception as e:
                logger.error(f"❌ 最终回调失败: {e}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"✅ 后处理完成，耗时: {elapsed_time:.2f}秒")
        return final_report
