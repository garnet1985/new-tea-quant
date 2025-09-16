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
    # Simulator callback methods:
    # ========================================================

    @staticmethod
    def simulate_single_day(stock_id: str, current_date: str, current_record: Dict[str, Any], 
                           all_data: List[Dict[str, Any]], current_investment: Optional[Dict[str, Any]], settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        模拟单日交易逻辑
        
        Args:
            stock_id: 股票ID
            current_date: 当前日期
            current_record: 当前日K线数据
            all_data: 所有数据（包含当前日及之前的所有数据）
            current_investment: 当前投资状态
            
        Returns:
            Dict[str, Any]: 包含以下字段的结果
                - new_investment: 新的投资（如果有）
                - settled_investments: 结算的投资列表
                - current_investment: 更新后的当前投资状态
        """
        new_investment = None
        settled_investments = []
        
        # 如果有投资，先检查是否需要结算
        if current_investment:
            # 更新投资的最大最小值跟踪
            HLSimulator._update_investment_tracking(current_investment, current_record)
            
            # 检查止盈止损目标
            should_settle, updated_investment = HLSimulator.check_targets(current_investment, current_record)
            
            if should_settle:
                # 结算投资
                HLSimulator.settle_investment(updated_investment)
                settled_investments.append(updated_investment)
                
                # 显示投资结果（模拟原HL simulator的行为）
                result = updated_investment.get('result', 'unknown')
                profit_rate = updated_investment.get('overall_profit_rate', 0) * 100
                duration_days = updated_investment.get('invest_duration_days', 0)
                
                if result == 'win':
                    if profit_rate >= 20:
                        result_dot = "🟢"
                        result_text = "盈利"
                    else:
                        result_dot = "🟡"
                        result_text = "微盈"
                elif result == 'loss':
                    if profit_rate <= -20:
                        result_dot = "🔴"
                        result_text = "亏损"
                    else:
                        result_dot = "🟠"
                        result_text = "微损"
                else:
                    result_dot = "⚪"
                    result_text = "未知"
                
                logger.info(f"🔍 投资结束: {stock_id} {result_dot} {result_text} | 收益率: {profit_rate:+.2f}% | 时长: {duration_days}天")
                
                current_investment = None  # 投资已结束
            else:
                current_investment = updated_investment
        
        # 如果没有投资，扫描新的投资机会
        if not current_investment:
            opportunity = HLSimulator.scan_single_stock(stock_id, all_data)
            if opportunity:
                new_investment = HistoricLowEntity.to_investment(opportunity)
                current_investment = new_investment
        
        return {
            'new_investment': new_investment,
            'settled_investments': settled_investments,
            'current_investment': current_investment
        }

    @staticmethod
    def summarize_single_stock(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        单股票汇总 - 从备份版本迁移
        
        Args:
            result: 单股票模拟结果
            
        Returns:
            Dict: 单股票汇总信息
        """
        stock_id = result.get('stock_id', 'unknown')
        investments = result.get('investments', [])
        settled_investments = result.get('settled_investments', [])
        
        # 统计投资数据
        total_investments = len(settled_investments)  # 只统计已结算的投资
        success_count = 0
        fail_count = 0
        open_count = len(investments)  # 未结算的投资
        total_profit = 0.0
        total_duration_days = 0
        total_roi = 0.0
        total_annual_return = 0.0
        
        # 处理已结算的投资
        for investment in settled_investments:
            result_type = investment.get('result', '')
            if result_type == 'win':
                success_count += 1
            elif result_type == 'loss':
                fail_count += 1
            
            # 累计收益和持续时间
            total_profit += investment.get('overall_profit', 0.0)
            total_duration_days += investment.get('invest_duration_days', 0)
            total_roi += investment.get('overall_profit_rate', 0.0)
            
            # 计算年化收益率
            duration_days = investment.get('invest_duration_days', 1)
            profit_rate = investment.get('overall_profit_rate', 0.0)
            annual_return = profit_rate * 365 / duration_days if duration_days > 0 else 0.0
            total_annual_return += annual_return
        
        # 计算平均值
        avg_profit = total_profit / total_investments if total_investments > 0 else 0.0
        avg_duration_days = total_duration_days / total_investments if total_investments > 0 else 0.0
        avg_roi = (total_roi / total_investments * 100) if total_investments > 0 else 0.0
        avg_annual_return = total_annual_return / total_investments if total_investments > 0 else 0.0
        
        # 计算胜率
        win_rate = (success_count / total_investments * 100) if total_investments > 0 else 0.0
        
        return {
            'total_investments': total_investments,
            'success_count': success_count,
            'fail_count': fail_count,
            'open_count': open_count,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'avg_duration_days': avg_duration_days,
            'avg_roi': avg_roi,
            'avg_annual_return': avg_annual_return,
            'investments': settled_investments  # 返回投资列表供session汇总使用
        }

    @staticmethod
    def summarize_session(stock_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        会话汇总 - 使用原来的HistoricLowEntity.to_session_summary逻辑
        
        Args:
            stock_summaries: 股票汇总列表
            
        Returns:
            Dict: 会话汇总信息
        """
        # 构建session_results格式
        session_results = []
        for stock_summary in stock_summaries:
            session_results.append({
                'investments': stock_summary.get('summary', {}).get('investments', [])
            })
        
        return HistoricLowEntity.to_session_summary(session_results)

    @staticmethod
    def present_final_report(final_report: Dict[str, Any]) -> None:
        """
        呈现最终报告 - 使用原来的HL simulator格式
        
        Args:
            final_report: 最终报告
        """
        session_summary = final_report.get('session_summary', {})
        
        print("\n" + "="*60)
        print("📊 HistoricLow 策略回测结果汇总")
        print("="*60)
        
        # 显示投资结果统计
        if session_summary:
            win_rate = session_summary.get('win_rate', 0)
            annual_return = session_summary.get('annual_return', 0)
            
            # 使用绿色点显示胜率（胜率超过60%显示绿色）
            win_rate_dot = "🟢" if win_rate >= 60 else "🔴"
            print(f"🎯 胜率: {win_rate_dot} {win_rate}%")
            
            # 使用绿色点显示年化收益率（年化收益率超过10%显示绿色）
            annual_return_dot = "🟢" if annual_return >= 15 else "🔴"
            print(f"📈 平均年化收益率: {annual_return_dot} {annual_return}%")
            
            print(f"⏱️  平均投资时长: {session_summary.get('avg_duration_days', 0)} 天")
            print(f"💰 平均ROI: {session_summary.get('avg_roi', 0)}%")
            
            print(f"📊 总投资次数: {session_summary.get('total_investments', 0)}")
            print(f"✅ 成功次数: {session_summary.get('win_count', 0)}")
            print(f"❌ 失败次数: {session_summary.get('loss_count', 0)}")
            
            # 显示详细统计
            print("<------------------------------------------->")
            print(f"🟢 盈利次数: {session_summary.get('green_dots', 0)} ({session_summary.get('green_dots', 0)/session_summary.get('total_investments', 1)*100:.1f}%)")
            print(f"🟡 微盈次数: {session_summary.get('yellow_dots', 0)} ({session_summary.get('yellow_dots', 0)/session_summary.get('total_investments', 1)*100:.1f}%)")
            print(f"🟠 微损次数: {session_summary.get('orange_dots', 0)} ({session_summary.get('orange_dots', 0)/session_summary.get('total_investments', 1)*100:.1f}%)")
            print(f"🔴 亏损次数: {session_summary.get('red_dots', 0)} ({session_summary.get('red_dots', 0)/session_summary.get('total_investments', 1)*100:.1f}%)")
            print("="*60)

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

    @staticmethod
    def split_daily_data(daily_records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        分割日线数据为冻结期和历史期
        
        Args:
            daily_data: 完整的日线数据列表
            
        Returns:
            freeze_records: 投资冻结期的数据
            history_records: 可以用来寻找机会的日线数据
        """
        # 获取配置参数
        freeze_days = strategy_settings['daily_data_requirements']['freeze_period_days']
        
        # 分割数据
        freeze_records = daily_records[-freeze_days:]  # 最近N个交易日（冻结期）
        history_records = daily_records[:-freeze_days]  # 之前的数据（历史期）
        
        return freeze_records, history_records

    @staticmethod
    def find_low_points(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """寻找历史低点"""
        low_points = []
        target_years = strategy_settings['daily_data_requirements']['low_points_ref_years']
        
        if not records:
            return low_points
        
        date_of_today = records[-1]['date']
        
        # 解析今天的日期
        from datetime import datetime, timedelta
        today = datetime.strptime(date_of_today, '%Y%m%d')
        
        for years_back in target_years:
            # 计算时间区间的开始日期（往前推years_back年）
            start_date = today - timedelta(days=years_back * 365)
            start_date_str = start_date.strftime('%Y%m%d')
            
            # 找到该时间区间内的所有记录
            period_records = [record for record in records 
                            if record['date'] >= start_date_str and record['date'] < date_of_today]
            
            if not period_records:
                continue
                
            # 找到该时间区间内的最低价格
            min_record = min(period_records, key=lambda x: float(x['close']))
            
            low_points.append(HistoricLowEntity.to_low_point(years_back, min_record))
        
        return low_points

    @staticmethod
    def find_opportunity_from_low_points(stock: Dict[str, Any], low_points: List[Dict[str, Any]], freeze_data: List[Dict[str, Any]], history_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """从历史低点中寻找投资机会"""
        if not low_points or not freeze_data:
            return None
        
        record_of_today = freeze_data[-1]
        
        # 检查是否在投资范围内
        for low_point in low_points:
            if HistoricLowService.is_in_invest_range(record_of_today, low_point, freeze_data):
                # 创建投资机会
                opportunity = HistoricLowEntity.to_opportunity(stock, record_of_today, low_point)
                return opportunity
        
        return None

    @staticmethod
    def scan_single_stock(stock_id: str, all_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """扫描单只股票的投资机会"""
        if not all_data:
            return None
        
        # 创建股票信息
        stock = {'id': stock_id}
        
        # 分割数据为冻结期和历史期
        freeze_records, history_records = HLSimulator.split_daily_data(all_data)
        
        # 寻找历史低点
        low_points = HLSimulator.find_low_points(history_records)
        
        # 从低点中寻找投资机会
        opportunity = HLSimulator.find_opportunity_from_low_points(stock, low_points, freeze_records, history_records)
        
        return opportunity