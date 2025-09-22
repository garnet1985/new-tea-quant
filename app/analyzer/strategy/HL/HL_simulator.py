#!/usr/bin/env python3
"""
HistoricLow策略模拟器 - 使用新的投资目标管理器
"""
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from loguru import logger
import json
import os
from pprint import pprint

from app.analyzer.analyzer_service import AnalyzerService
from app.analyzer.strategy.HL.HL_service import HistoricLowService
from app.analyzer.components.investment import InvestmentGoalManager, InvestmentRecorder
from app.analyzer.components.entity import EntityBuilder
from app.analyzer.components.enum.common_enum import InvestmentResult

from app.data_source.data_source_service import DataSourceService
from app.analyzer.strategy.HL.settings import settings
from .HL_entity import HistoricLowEntity


class HistoricLowSimulator:
    def __init__(self, strategy):
        
        self.strategy = strategy

        # init tracker
        self.invest_recorder = InvestmentRecorder(settings['folder_name'])

        # 汇总收集器（单线程汇总，无需锁）
        self.session_results = []
        
        # 是否启用详细日志
        self.is_verbose = False

    # ========================================================
    # Core logic:
    # ========================================================
    
    # @staticmethod
    # def simulate_one_day(stock: Dict[str, Any], daily_k_lines: List[Dict[str, Any]], tracker: Dict[str, Any]) -> None:
    #     record_of_today = daily_k_lines[-1]

    #     # 检查现有投资的目标
    #     if stock['id'] in tracker['investing']:
    #         investment = tracker['investing'][stock['id']]
    #         goal_manager = InvestmentGoalManager(settings['goal'])
    #         is_investment_ended, updated_investment = goal_manager.check_targets(investment, record_of_today)
            
    #         if is_investment_ended:
    #             goal_manager = InvestmentGoalManager(settings['goal'])
    #             goal_manager.settle_investment(updated_investment)
    #             settled_entity = EntityBuilder.to_settled_investment(
    #                 investment=updated_investment,
    #                 end_date=updated_investment.get('end_date'),
    #                 result=updated_investment.get('result')
    #             )
    #             tracker['settled'].append(settled_entity)
    #             del tracker['investing'][stock['id']]
    #         else:
    #             tracker['investing'][stock['id']] = updated_investment
    #             HistoricLowSimulator.update_investment_max_min_close(updated_investment, record_of_today)

    #     # 扫描新的投资机会
    #     opportunity = HistoricLowSimulator.scan_single_stock(stock, daily_k_lines)
    #     if opportunity:
    #         # 使用通用构造器创建基础投资实体，策略层通过 extra_fields 注入 tracking/opportunity 等自定义字段
    #         goal_manager = InvestmentGoalManager(settings['goal'])
    #         targets = goal_manager.create_investment_targets()
    #         extra_fields = {
    #             'result': InvestmentResult.OPEN.value,
    #             'end_date': '',
    #             'tracking': {
    #                 'max_close_reached': { 'price': 0, 'date': '', 'ratio': 0 },
    #                 'min_close_reached': { 'price': 0, 'date': '', 'ratio': 0 },
    #             },
    #             'opportunity': opportunity
    #         }
    #         tracker['investing'][stock['id']] = EntityBuilder.to_investment(
    #             stock={'id': stock['id'], 'name': opportunity.get('stock', {}).get('name', '')},
    #             start_date=opportunity['date'],
    #             purchase_price=opportunity['price'],
    #             targets=targets,
    #             extra_fields=extra_fields
    #         )

    



    # @staticmethod
    # def settle_open_investment(investment: Dict[str, Any], final_price: float) -> Dict[str, Any]:
    #     """结算Open状态的投资（模拟结束时仍在持仓）"""
    #     # 创建投资目标管理器
    #     goal_manager = InvestmentGoalManager(settings['goal'])
        
    #     # 使用目标管理器结算未结束的投资
    #     goal_manager.settle_open_investment(investment, final_price, '20241231')
        
    #     # 使用通用实体构造器生成标准结算实体
    #     settled = EntityBuilder.to_settled_investment(
    #         investment=investment,
    #         end_date=investment.get('end_date'),
    #         result=investment.get('result')
    #     )
    #     return settled

    # ========================================================
    # Main steps:
    # ========================================================

    # def is_invest_settings_valid(self) -> bool:
    #     """检查投资设置是否有效"""
    #     try:
    #         # 必须提供文件夹名用于结果存储
    #         if 'folder_name' not in settings or not settings['folder_name']:
    #             logger.error("缺少策略文件夹名配置 folder_name")
    #             return False

    #         goal_config = settings.get('goal', {})
    #         if not goal_config:
    #             logger.error("缺少投资目标配置")
    #             return False
            
    #         take_profit = goal_config.get('take_profit', {})
    #         stop_loss = goal_config.get('stop_loss', {})
            
    #         if not take_profit or not stop_loss:
    #             logger.error("缺少止盈或止损配置")
    #             return False
            
    #         return True
    #     except Exception as e:
    #         logger.error(f"投资设置验证失败: {e}")
    #         return False
	
    # def get_stock_list_by_test_mode(self) -> List[Dict[str, Any]]:
    #     """根据测试模式获取股票列表"""
    #     test_mode = settings.get('test_mode', {})
    #     test_amount = test_mode.get('test_amount', 10)
    #     start_idx = test_mode.get('start_idx', 0)
			
    #     # 获取股票列表
    #     stock_list = DataSourceService.get_filtered_stock_index()
        
    #     # 根据测试模式截取
    #     end_idx = start_idx + test_amount
    #     return stock_list[start_idx:end_idx]

    # def build_jobs(self, stock_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    #     """构建模拟任务"""
    #     jobs = []
    #     for stock in stock_list:
    #         job = {
    #             'stock': stock,
    #             'data': DataSourceService.get_stock_kline_data(stock['id'], 'daily')
    #         }
    #         jobs.append(job)
    #     return jobs

    # def run_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    #     """运行模拟任务"""
    #     results = []
    #     tracker = {'investing': {}, 'settled': []}
        
    #     for job in jobs:
    #         stock = job['stock']
    #         daily_k_lines = job['data']
            
    #         # 模拟每一天
    #         for i in range(len(daily_k_lines)):
    #             current_data = daily_k_lines[:i+1]
    #             HistoricLowSimulator.simulate_one_day(stock, current_data, tracker)
            
    #         # 处理未结束的投资
    #         for investment in list(tracker['investing'].values()):
    #             final_price = daily_k_lines[-1]['close'] if daily_k_lines else 0
    #             settled_entity = HistoricLowSimulator.settle_open_investment(investment, final_price)
    #             tracker['settled'].append(settled_entity)
            
    #         # 保存结果
    #         result = {
    #             'stock_id': stock['id'],
    #             'investments': tracker['investing'].get(stock['id'], {}),
    #             'settled_investments': [inv for inv in tracker['settled'] if inv.get('stock', {}).get('id') == stock['id']]
    #         }
    #         results.append(result)
            
    #         # 重置tracker
    #         tracker = {'investing': {}, 'settled': []}
        
    #     return results

    def generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成汇总信息"""
        total_investments = 0
        win_count = 0
        loss_count = 0
        open_count = 0
        
        for result in results:
            settled_investments = result.get('settled_investments', [])
            total_investments += len(settled_investments)
            
            for investment in settled_investments:
                if investment.get('result') == InvestmentResult.WIN.value:
                    win_count += 1
                elif investment.get('result') == InvestmentResult.LOSS.value:
                    loss_count += 1
                else:
                    open_count += 1
        
        win_rate = (win_count / total_investments) if total_investments > 0 else 0
        
        return {
            'total_investments': total_investments,
            'win_count': win_count,
            'loss_count': loss_count,
            'open_count': open_count,
            'win_rate': win_rate
        }

    def present_investment_summary(self, session_summary: Dict[str, Any]) -> None:
        """展示投资汇总"""
        logger.info("📊 HistoricLow 策略模拟报告")
        logger.info("=" * 60)
        logger.info(f"📈 总投资次数: {session_summary['total_investments']}")
        logger.info(f"✅ 成功次数: {session_summary['win_count']}")
        logger.info(f"❌ 失败次数: {session_summary['loss_count']}")
        logger.info(f"⏳ 未结束次数: {session_summary['open_count']}")
        logger.info(f"🎯 投资成功率: {session_summary['win_rate']:.1%}")
	
	# ========================================================
    # Simulator callback methods:
	# ========================================================
	
    # @staticmethod
    # def simulate_single_day(stock_id: str, current_date: str, current_record: Dict[str, Any], 
    #                        all_data: List[Dict[str, Any]], current_investment: Optional[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     模拟单日交易逻辑
        
    #     Args:
    #         stock_id: 股票ID
    #         current_date: 当前日期
    #         current_record: 当前日K线数据
    #         all_data: 所有数据（包含当前日及之前的所有数据）
    #         current_investment: 当前投资状态
            
    #     Returns:
    #         Dict[str, Any]: 包含以下字段的结果
    #             - new_investment: 新的投资（如果有）
    #             - settled_investments: 结算的投资列表
    #             - current_investment: 更新后的当前投资状态
    #     """
    #     new_investment = None
    #     settled_investments = []
        
    #     # 如果有投资，先检查是否需要结算
    #     if current_investment:
    #         # 更新投资的最大最小值跟踪
    #         HistoricLowSimulator._update_investment_tracking(current_investment, current_record)
            
    #         # 检查止盈止损目标
    #         goal_manager = InvestmentGoalManager(settings['goal'])
    #         should_settle, updated_investment = goal_manager.check_targets(current_investment, current_record)
            
    #         if should_settle:
    #             # 结算投资（直接调用公用方法）
    #             goal_manager = InvestmentGoalManager(settings['goal'])
    #             goal_manager.settle_investment(updated_investment)
    #             settled_entity = EntityBuilder.to_settled_investment(
    #                 investment=updated_investment,
    #                 end_date=updated_investment.get('end_date'),
    #                 result=updated_investment.get('result')
    #             )
    #             settled_investments.append(settled_entity)
                
    #             # 显示投资结果（模拟原HL simulator的行为）
    #             result = settled_entity.get('result', 'unknown')
    #             profit_rate = settled_entity.get('overall_profit_rate', 0) * 100
    #             duration_days = settled_entity.get('invest_duration_days', 0)
                
    #             if result == 'win':
    #                 if profit_rate >= 20:
    #                     result_dot = "🟢"
    #                     result_text = "盈利"
    #                 else:
    #                     result_dot = "🟡"
    #                     result_text = "微盈"
    #             elif result == 'loss':
    #                 if profit_rate <= -20:
    #                     result_dot = "🔴"
    #                     result_text = "亏损"
    #                 else:
    #                     result_dot = "🟠"
    #                     result_text = "微损"
    #             else:
    #                 result_dot = "⚪"
    #                 result_text = "未知"
                
    #             logger.info(f"🔍 投资结束: {stock_id} {result_dot} {result_text} | 收益率: {profit_rate:+.2f}% | 时长: {duration_days}天")
                
    #             current_investment = None  # 投资已结束
    #         else:
    #             current_investment = updated_investment
        
    #     # 如果没有投资，扫描新的投资机会
    #     if not current_investment:
    #         opportunity = HistoricLowSimulator.scan_single_stock(stock_id, all_data)
    #         if opportunity:
    #             # 使用通用构造器创建基础投资实体，策略层通过 extra_fields 注入 tracking/opportunity 等自定义字段
    #             goal_manager = InvestmentGoalManager(settings['goal'])
    #             targets = goal_manager.create_investment_targets()
    #             extra_fields = {
    #                 'result': InvestmentResult.OPEN.value,
    #                 'end_date': '',
    #                 'tracking': {
    #                     'max_close_reached': { 'price': 0, 'date': '', 'ratio': 0 },
    #                     'min_close_reached': { 'price': 0, 'date': '', 'ratio': 0 },
    #                 },
    #                 'opportunity': opportunity
    #             }
    #             new_investment = EntityBuilder.to_investment(
    #                 stock={'id': stock_id, 'name': opportunity.get('stock', {}).get('name', '')},
    #                 start_date=opportunity['date'],
    #                 purchase_price=opportunity['price'],
    #                 targets=targets,
    #                 extra_fields=extra_fields
    #             )
    #             current_investment = new_investment
        
    #     return {
    #         'new_investment': new_investment,
    #         'settled_investments': settled_investments,
    #         'current_investment': current_investment
    #     }

    # @staticmethod
    # def summarize_single_stock(result: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     单股票汇总 - 使用通用计算 + entity builder 封装
        
    #     Args:
    #         result: 单股票模拟结果
            
    #     Returns:
    #         Dict: 标准结构 { 'stock_id', 'summary': {...} }
    #     """
    #     stock_id = result.get('stock_id', 'unknown')
    #     settled_investments = result.get('settled_investments', [])

    #     # 用通用计算产出核心字段
    #     summary_core = EntityBuilder.compute_stock_summary_core(settled_investments)

    #     # 通过 entity builder 生成标准结构，并保留 investments 供 session 汇总使用
    #     return EntityBuilder.to_stock_summary(
    #         stock_id=stock_id,
    #         summary_core=summary_core,
    #         extra_fields={'investments': settled_investments},
    #     )
	
    @staticmethod
    def summarize_session(stock_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        会话汇总 - 使用原来的HistoricLowEntity.to_session_summary逻辑
        
        Args:
            stock_summaries: 股票汇总列表
            
        Returns:
            Dict: 会话汇总信息
        """
        # 构建 session_results（标准输入格式）
        session_results = []
        for stock_summary in stock_summaries:
            session_results.append({
                'investments': stock_summary.get('summary', {}).get('investments', [])
            })

        # 计算一个基础汇总核心字段（可复用的通用逻辑）
        summary_core = EntityBuilder.compute_session_summary_core(session_results)

        # 用通用 Entity Builder 生成一个基础的 session summary
        base_summary = EntityBuilder.to_session_summary(summary_core)

        # 暴露一个自定义扩展点：允许策略在保存前做二次加工
        return HistoricLowSimulator.customize_session_summary(base_summary, session_results)

    @staticmethod
    def customize_session_summary(base_summary: Dict[str, Any], session_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """策略级自定义汇总扩展点。

        默认实现：复用 HistoricLowEntity.to_session_summary 的详细统计，并与基础汇总合并。
        外部可替换为其他计算逻辑。
        """
        try:
            advanced = HistoricLowEntity.to_session_summary(session_results)
            # 合并：以 advanced 为主，保留 base_summary 中未覆盖字段
            merged = dict(base_summary)
            merged.update(advanced or {})
            return merged
        except Exception:
            # 回退：出现异常则直接返回基础汇总
            return base_summary
	
    # ========================================================
    # Helper methods:
    # ========================================================
	
    @staticmethod
    def _update_investment_tracking(investment: Dict[str, Any], current_record: Dict[str, Any]) -> None:
        """更新投资的最大最小值跟踪"""
        # 更新最高价
        if current_record['close'] > investment['tracking']['max_close_reached']['price']:
            investment['tracking']['max_close_reached']['price'] = current_record['close']
            investment['tracking']['max_close_reached']['date'] = current_record['date']
            investment['tracking']['max_close_reached']['ratio'] = (current_record['close'] - investment['purchase_price']) / investment['purchase_price']
		
		# 更新最低价
        current_min_price = investment['tracking']['min_close_reached']['price']
        if current_min_price == 0 or current_record['close'] < current_min_price:
            investment['tracking']['min_close_reached']['price'] = current_record['close']
            investment['tracking']['min_close_reached']['date'] = current_record['date']
            investment['tracking']['min_close_reached']['ratio'] = (current_record['close'] - investment['purchase_price']) / investment['purchase_price']