#!/usr/bin/env python3
"""
HistoricLow策略模拟器 - 使用新的投资目标管理器
"""
from typing import Dict, List, Any, Tuple
from datetime import datetime
from loguru import logger
import json
import os
from pprint import pprint

from app.analyzer.analyzer_service import AnalyzerService
from app.analyzer.strategy.historicLow.strategy_service import HistoricLowService
from app.analyzer.libs.simulator.simulator_enum import InvestmentResult
from app.analyzer.libs.investment import InvestmentGoalManager, InvestmentRecorder

from app.data_source.data_source_service import DataSourceService
from app.analyzer.strategy.historicLow.strategy_settings import strategy_settings
from .strategy_entity import HistoricLowEntity


class HLSimulator:
    def __init__(self, strategy):
        self.strategy = strategy
        
        # init tracker
        self.invest_recorder = InvestmentRecorder("historicLow")

        # 汇总收集器（单线程汇总，无需锁）
        self.session_results = []
        
        # 是否启用详细日志
        self.is_verbose = False
    
    # ========================================================
    # External (Bridge) APIs:
    # ========================================================

    def test_strategy(self) -> None:
        if not self.is_invest_settings_valid():
            return

        stock_idx = self.get_stock_list_by_test_mode()
        jobs = self.build_jobs(stock_idx)
        results = self.run_jobs(jobs)
        session_summary = self.generate_summary(results)
        self.present_investment_summary(session_summary)

    # ========================================================
    # Core logic:
    # ========================================================
    
    @staticmethod
    def simulate_one_day(stock: Dict[str, Any], daily_k_lines: List[Dict[str, Any]], tracker: Dict[str, Any]) -> None:
        record_of_today = daily_k_lines[-1]

        # 检查现有投资的目标
        if stock['id'] in tracker['investing']:
            investment = tracker['investing'][stock['id']]
            is_investment_ended, updated_investment = HLSimulator.check_targets(investment, record_of_today)
            
            if is_investment_ended:
                HLSimulator.settle_investment(updated_investment)
                tracker['settled'].append(updated_investment)
                del tracker['investing'][stock['id']]
            else:
                tracker['investing'][stock['id']] = updated_investment
                HLSimulator.update_investment_max_min_close(updated_investment, record_of_today)

        # 扫描新的投资机会
        opportunity = HLSimulator.scan_single_stock(stock, daily_k_lines)
        if opportunity:
            tracker['investing'][stock['id']] = HistoricLowEntity.to_investment(opportunity)

    @staticmethod
    def check_targets(investment: Dict[str, Any], record_of_today: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        # 创建投资目标管理器
        goal_manager = InvestmentGoalManager(strategy_settings['goal'])
        
        # 使用目标管理器检查目标
        is_investment_ended, updated_investment = goal_manager.check_targets(investment, record_of_today)
        
        return is_investment_ended, updated_investment

    @staticmethod
    def update_investment_max_min_close(investment: Dict[str, Any], record_of_today: Dict[str, Any]) -> None:
        # 更新最高价
        if record_of_today['close'] > investment['tracking']['max_close_reached']['price']:
            investment['tracking']['max_close_reached']['price'] = record_of_today['close']
            investment['tracking']['max_close_reached']['date'] = record_of_today['date']
            investment['tracking']['max_close_reached']['ratio'] = (record_of_today['close'] - investment['purchase_price']) / investment['purchase_price']
        
        # 更新最低价
        current_min_price = investment['tracking']['min_close_reached']['price']
        if current_min_price == 0 or record_of_today['close'] < current_min_price:
            investment['tracking']['min_close_reached']['price'] = record_of_today['close']
            investment['tracking']['min_close_reached']['date'] = record_of_today['date']
            investment['tracking']['min_close_reached']['ratio'] = (record_of_today['close'] - investment['purchase_price']) / investment['purchase_price']

    @staticmethod
    def settle_investment(investment: Dict[str, Any]) -> None:
        # 创建投资目标管理器
        goal_manager = InvestmentGoalManager(strategy_settings['goal'])
        
        # 使用目标管理器结算投资
        goal_manager.settle_investment(investment)
        
        # 计算投资时长
        investment['invest_duration_days'] = AnalyzerService.get_duration_in_days(investment['start_date'], investment['end_date'])

    @staticmethod
    def settle_open_investment(investment: Dict[str, Any], final_price: float) -> None:
        """结算Open状态的投资（模拟结束时仍在持仓）"""
        # 创建投资目标管理器
        goal_manager = InvestmentGoalManager(strategy_settings['goal'])
        
        # 使用目标管理器结算未结束的投资
        goal_manager.settle_open_investment(investment, final_price, '20241231')
        
        # 计算投资时长
        investment['invest_duration_days'] = AnalyzerService.get_duration_in_days(investment['start_date'], investment['end_date'])

    # ========================================================
    # Main steps:
    # ========================================================

    def is_invest_settings_valid(self) -> bool:
        """检查投资设置是否有效"""
        try:
            goal_config = strategy_settings.get('goal', {})
            if not goal_config:
                logger.error("缺少投资目标配置")
                return False
            
            take_profit = goal_config.get('take_profit', {})
            stop_loss = goal_config.get('stop_loss', {})
            
            if not take_profit or not stop_loss:
                logger.error("缺少止盈或止损配置")
                return False
            
            return True
        except Exception as e:
            logger.error(f"投资设置验证失败: {e}")
            return False

    def get_stock_list_by_test_mode(self) -> List[Dict[str, Any]]:
        """根据测试模式获取股票列表"""
        test_mode = strategy_settings.get('test_mode', {})
        test_amount = test_mode.get('test_amount', 10)
        start_idx = test_mode.get('start_idx', 0)
        
        # 获取股票列表
        stock_list = DataSourceService.get_filtered_stock_index()
        
        # 根据测试模式截取
        end_idx = start_idx + test_amount
        return stock_list[start_idx:end_idx]

    def build_jobs(self, stock_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """构建模拟任务"""
        jobs = []
        for stock in stock_list:
            job = {
                'stock': stock,
                'data': DataSourceService.get_stock_kline_data(stock['id'], 'daily')
            }
            jobs.append(job)
        return jobs

    def run_jobs(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """运行模拟任务"""
        results = []
        tracker = {'investing': {}, 'settled': []}
        
        for job in jobs:
            stock = job['stock']
            daily_k_lines = job['data']
            
            # 模拟每一天
            for i in range(len(daily_k_lines)):
                current_data = daily_k_lines[:i+1]
                HLSimulator.simulate_one_day(stock, current_data, tracker)
            
            # 处理未结束的投资
            for investment in tracker['investing'].values():
                final_price = daily_k_lines[-1]['close'] if daily_k_lines else 0
                HLSimulator.settle_open_investment(investment, final_price)
                tracker['settled'].append(investment)
            
            # 保存结果
            result = {
                'stock_id': stock['id'],
                'investments': tracker['investing'].get(stock['id'], {}),
                'settled_investments': [inv for inv in tracker['settled'] if inv.get('stock', {}).get('id') == stock['id']]
            }
            results.append(result)
            
            # 重置tracker
            tracker = {'investing': {}, 'settled': []}
        
        return results

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
    # Stock scanning logic:
    # ========================================================

    @staticmethod
    def scan_single_stock(stock: Dict[str, Any], daily_k_lines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """扫描单只股票的投资机会"""
        # 这里应该实现具体的投资机会扫描逻辑
        # 暂时返回None，表示没有投资机会
        return None