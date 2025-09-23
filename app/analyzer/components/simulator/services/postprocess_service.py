"""
后处理服务模块

负责模拟结果的汇总、统计和报告生成
"""

from typing import Dict, List, Any, Optional, Callable
from loguru import logger
from app.analyzer.analyzer_service import AnalyzerService
from app.analyzer.components.investment import InvestmentRecorder
from app.analyzer.components.enum import InvestmentResult
from utils.icon.icon_service import IconService

class PostprocessService:
    """后处理服务类"""


    @staticmethod
    def summarize_stock(simulate_result: Dict[str, Any], module_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        汇总单股票结果
        """
        stock_summary = PostprocessService.summarize_stock_by_default_way(simulate_result)

        import importlib
        strategy_class_name = module_info.get('strategy_class_name', '')
        strategy_module_path = module_info.get('strategy_module_path', '')
        # expose to strategy class to add any extra fields
        strategy_module = importlib.import_module(strategy_module_path)
        strategy_class = getattr(strategy_module, strategy_class_name)

        stock_summary = strategy_class.on_summarize_stock(stock_summary, simulate_result)

        return stock_summary

    @staticmethod
    def summarize_stock_by_default_way(simulate_result: Dict[str, Any]) -> Dict[str, Any]:

        settled = simulate_result.get('settled') or []

        total = len(settled)
        total_win = 0
        total_loss = 0
        total_open = 0

        total_profit = 0.0
        total_duration = 0.0
        total_roi = 0.0
        total_annual_return = 0.0

        profitable_count = 0
        minor_profitable_count = 0
        unprofitable_count = 0
        minor_unprofitable_count = 0

        investments = []

        for inv in settled:

            result = inv.get('result')
            if result == InvestmentResult.WIN.value:
                total_win += 1
            elif result == InvestmentResult.LOSS.value:
                total_loss += 1
            elif result == InvestmentResult.OPEN.value:
                total_open += 1

            total_profit += inv['overall_profit']
            total_duration += inv['invest_duration_days']   
            total_roi += inv['overall_profit_rate'] * 100.0
            total_annual_return += inv['overall_annual_return']

            if inv['overall_profit_rate'] >= 0.2:
                profitable_count += 1
            elif inv['overall_profit_rate'] >= 0 and inv['overall_profit_rate'] < 0.2:
                minor_profitable_count += 1
            elif inv['overall_profit_rate'] < 0 and inv['overall_profit_rate'] > -0.2:
                minor_unprofitable_count += 1
            else:
                unprofitable_count += 1

            investments.append({
                'result': result,

                'start_date': inv['start_date'],
                'end_date': inv['end_date'],
                'purchase_price': inv['purchase_price'],
                'duration_in_days': inv['invest_duration_days'],

                'overall_profit': inv['overall_profit'],
                'overall_profit_rate': inv['overall_profit_rate'],
                'overall_annual_return': inv['overall_annual_return'],
                
                'tracking': inv['tracking'],

                'completed_targets': inv['targets']['completed'],

                'extra_fields': inv['extra_fields'],
            })

        avg_profit = AnalyzerService.to_ratio(total_profit, total)
        avg_duration_in_days = AnalyzerService.to_ratio(total_duration, total)
        avg_roi = AnalyzerService.to_ratio(total_roi, total)
        avg_annual_return = AnalyzerService.to_ratio(total_annual_return, total)

        win_rate = AnalyzerService.to_ratio((profitable_count + minor_profitable_count), total, 3)

        summary = {
            'total_investments': total,
            'total_win': total_win,
            'total_loss': total_loss,
            'total_open': total_open,

            'profitable': profitable_count,
            'minor_profitable': minor_profitable_count,
            'unprofitable': unprofitable_count,
            'minor_unprofitable': minor_unprofitable_count,

            'win_rate': round(win_rate, 1),
            'total_profit': round(total_profit, 2),
            'avg_profit': round(avg_profit, 2),
            'avg_duration_in_days': round(avg_duration_in_days, 1),
            'avg_roi': round(avg_roi, 2),
            'avg_annual_return': round(avg_annual_return, 2),
        }

        summarized_stock = {
            'stock': simulate_result['stock'],
            'investments': investments,
            'summary': summary,
        }

        return summarized_stock
    
    @staticmethod
    def summarize_session(stock_summaries: List[Dict[str, Any]], module_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        汇总整个会话结果
        
        Args:
            stock_summaries: 股票汇总结果列表
            module_info: 模块信息
            
        Returns:
            Dict: 会话汇总结果
        """
        base_session_summary = PostprocessService.summarize_session_by_default_way(stock_summaries)

        import importlib
        strategy_class_name = module_info.get('strategy_class_name', '')
        strategy_module_path = module_info.get('strategy_module_path', '')
        # expose to strategy class to add any extra fields
        strategy_module = importlib.import_module(strategy_module_path)
        strategy_class = getattr(strategy_module, strategy_class_name)

        session_summary = strategy_class.on_summarize_session(base_session_summary)

        return session_summary


    @staticmethod
    def summarize_session_by_default_way(stock_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        默认的会话汇总逻辑
        
        Args:
            stock_summaries: 股票汇总结果列表
            
        Returns:
            Dict: 会话汇总结果
        """
        total_investments = 0
        total_win = 0
        total_loss = 0
        total_open = 0

        profitable = 0
        minor_profitable = 0
        unprofitable = 0
        minor_unprofitable = 0
        
        total_roi = 0.0
        total_annual_return = 0.0
        total_duration_days = 0.0
        
        stocks_with_opportunities = len(stock_summaries)

        for stock_summary in stock_summaries:

            summary = stock_summary.get('summary', {})
            
            investment_count = summary.get('total_investments', 0)

            if investment_count > 0:

                total_investments += investment_count
                total_win += summary.get('total_win', 0)
                total_loss += summary.get('total_loss', 0)
                total_open += summary.get('total_open', 0)

                profitable += summary.get('profitable', 0)
                minor_profitable += summary.get('minor_profitable', 0)
                unprofitable += summary.get('unprofitable', 0)
                minor_unprofitable += summary.get('minor_unprofitable', 0)

                # 加权平均计算
                total_roi += summary.get('avg_roi', 0) * investment_count
                total_annual_return += summary.get('avg_annual_return', 0) * investment_count
                total_duration_days += summary.get('avg_duration_in_days', 0) * investment_count
        
        # 计算整体平均值
        avg_roi = AnalyzerService.to_ratio(total_roi, total_investments)
        avg_duration_days = AnalyzerService.to_ratio(total_duration_days, total_investments)
        
        # 因为每只股票的年化收益率已经基于其整体表现计算
        avg_annual_return = AnalyzerService.to_ratio(total_annual_return, total_investments)
        
        # 计算整体成功率
        total_successful = profitable + minor_profitable
        win_rate = AnalyzerService.to_percent(total_successful, total_investments)
        
        # 计算各种比例
        profitable_ratio = AnalyzerService.to_percent(profitable, total_investments)
        unprofitable_ratio = AnalyzerService.to_percent(unprofitable, total_investments)
        minor_profit_ratio = AnalyzerService.to_percent(minor_profitable, total_investments)
        minor_loss_ratio = AnalyzerService.to_percent(minor_unprofitable, total_investments)
        
        default_session_summary = {
            'win_rate': win_rate,

            'avg_roi': avg_roi,
            'avg_annual_return': avg_annual_return,
            'avg_duration_in_days': avg_duration_days,

            'total_investments': total_investments,
            'total_open_investments': total_open,
            'total_win_investments': total_win,
            'total_loss_investments': total_loss,

            'profitable_count': profitable,
            'minor_profitable_count': minor_profitable,
            'unprofitable_count': unprofitable,
            'minor_unprofitable_count': minor_unprofitable,

            'profitable_ratio': profitable_ratio,
            'unprofitable_ratio': unprofitable_ratio,
            'minor_profit_ratio': minor_profit_ratio,
            'minor_loss_ratio': minor_loss_ratio,

            'stocks_have_opportunities': stocks_with_opportunities,
        }

        return default_session_summary
    
    @staticmethod
    def present_session_report(session_summary: Dict[str, Any], strategy_name: str = '当前') -> None:
        """
        通用的控制台展示方法

        Args:
            session_summary: 会话汇总结果
            strategy_name: 策略名称
            
        Returns:
            None
        """
        print("\n" + "="*60)
        print(f"📊 {strategy_name}策略回测结果")
        print("="*60)
        if session_summary:
            win_rate = session_summary.get('win_rate', 0)
            avg_annual_return = session_summary.get('avg_annual_return', 0)
            avg_roi = session_summary.get('avg_roi', 0)

            if win_rate >= 60:
                win_rate_dot = IconService.get('green_dot')
            else:
                win_rate_dot = IconService.get('red_dot')
            print(f"🎯 胜率: {win_rate_dot} {win_rate:.1f}%")

            if avg_roi >= 5:
                avg_roi_dot = IconService.get('green_dot')
            else:
                avg_roi_dot = IconService.get('red_dot')
            print(f"{IconService.get('money')} 平均每笔投资回报率(ROI): {avg_roi_dot} {avg_roi:.1f}%")

            if avg_annual_return >= 15:
                annual_return_dot = IconService.get('green_dot')
            else:
                annual_return_dot = IconService.get('red_dot')
            print(f"{IconService.get('upward_trend')} 平均年化收益率: {annual_return_dot} {avg_annual_return:.1f}%")
            
            print(f"{IconService.get('clock')} 平均投资时长: {session_summary.get('avg_duration_in_days', 0):.1f} 天")
            print(f"{IconService.get('bar_chart')} 总投资次数: {session_summary.get('total_investments', 0)}")
            print(f"{IconService.get('success')} 成功次数: {session_summary.get('total_win_investments', 0)}")
            print(f"{IconService.get('error')} 失败次数: {session_summary.get('total_loss_investments', 0)}")
            print(f"{IconService.get('ongoing')} 未完成次数: {session_summary.get('total_open_investments', 0)}")
            print("<------------------------------------------->")
            print(f"{IconService.get('green_dot')} 盈利次数: {session_summary.get('profitable_count', 0)} ({session_summary.get('profitable_ratio', 0):.1f}%)")
            print(f"{IconService.get('yellow_dot')} 微盈次数: {session_summary.get('minor_profitable_count', 0)} ({session_summary.get('minor_profit_ratio', 0):.1f}%)")
            print(f"{IconService.get('orange_dot')} 微损次数: {session_summary.get('minor_unprofitable_count', 0)} ({session_summary.get('minor_loss_ratio', 0):.1f}%)")
            print(f"{IconService.get('red_dot')} 亏损次数: {session_summary.get('unprofitable_count', 0)} ({session_summary.get('unprofitable_ratio', 0):.1f}%)")
            print("="*60)