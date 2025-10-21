"""
后处理服务模块

负责模拟结果的汇总、统计和报告生成
"""

from typing import Dict, List, Any
from loguru import logger
from app.analyzer.analyzer_service import AnalyzerService
from app.analyzer.enums import InvestmentResult
from utils.icon.icon_service import IconService

class PostprocessService:
    """后处理服务类"""


    @staticmethod
    def summarize_stock(simulate_result: Dict[str, Any], strategy_class: Any) -> Dict[str, Any]:
        """
        汇总单股票结果
        """
        stock_summary = PostprocessService.summarize_stock_by_default_way(simulate_result)

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
            # ROI 统一标准：内部存储为小数（0.20 = 20%），显示时转换为百分比
            total_roi += inv['overall_profit_rate']

            # 盈亏分类：使用小数比较（0.2 = 20%）
            if inv['overall_profit_rate'] >= 0.2:
                profitable_count += 1
            elif inv['overall_profit_rate'] >= 0 and inv['overall_profit_rate'] < 0.2:
                minor_profitable_count += 1
            elif inv['overall_profit_rate'] < 0 and inv['overall_profit_rate'] > -0.2:
                minor_unprofitable_count += 1
            else:
                unprofitable_count += 1

            investment_data = {
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
            }
            
            # 只在有 extra_fields 时才添加
            if 'extra_fields' in inv and inv['extra_fields']:
                investment_data['extra_fields'] = inv['extra_fields']
            
            investments.append(investment_data)

        avg_profit = AnalyzerService.to_ratio(total_profit, total)
        avg_duration_in_days = AnalyzerService.to_ratio(total_duration, total)
        avg_roi = AnalyzerService.to_ratio(total_roi, total)
        
        annual_return = AnalyzerService.get_annual_return(avg_roi, avg_duration_in_days)
        annual_return_in_trading_days = AnalyzerService.get_annual_return(avg_roi, avg_duration_in_days, is_trading_days=True)

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
            'avg_roi': round(avg_roi, 4),  # 从 2 位改为 4 位小数，避免小 ROI 被四舍五入为 0
            'annual_return': round(annual_return, 2),
            'annual_return_in_trading_days': round(annual_return_in_trading_days, 2),
        }

        summarized_stock = {
            'stock': simulate_result['stock'],
            'investments': investments,
            'summary': summary,
        }

        return summarized_stock
    
    @staticmethod
    def summarize_session(stock_summaries: List[Dict[str, Any]], strategy_class: Any) -> Dict[str, Any]:
        """
        汇总整个会话结果
        
        Args:
            stock_summaries: 股票汇总结果列表
            strategy_class: 策略类
            
        Returns:
            Dict: 会话汇总结果
        """
        base_session_summary = PostprocessService.summarize_session_by_default_way(stock_summaries)

        session_summary = strategy_class.on_summarize_session(base_session_summary, stock_summaries)

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
        total_duration_days = 0.0
        
        stocks_with_opportunities = len(stock_summaries)

        for stock_summary in stock_summaries:

            summary = stock_summary.get('summary', {})
            stock_name = stock_summary.get('stock', {}).get('name', 'Unknown')
            
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
                stock_avg_roi = summary.get('avg_roi', 0)
                stock_roi_contribution = stock_avg_roi * investment_count
                total_roi += stock_roi_contribution
                total_duration_days += summary.get('avg_duration_in_days', 0) * investment_count
        
        # 计算整体平均值 - avg_roi 需要更高精度（4位小数）以避免小ROI被舍入为0
        avg_roi = AnalyzerService.to_ratio(total_roi, total_investments, decimals=4)
        avg_duration_days = AnalyzerService.to_ratio(total_duration_days, total_investments)
        
        # 使用"平均ROI + 平均持有期"推导会话级平均年化，更稳健
        annual_return = AnalyzerService.get_annual_return(avg_roi, avg_duration_days)
        annual_return_in_trading_days = AnalyzerService.get_annual_return(avg_roi, avg_duration_days, is_trading_days=True)
        
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
            'annual_return': annual_return,
            'annual_return_in_trading_days': annual_return_in_trading_days,
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
    def present_session_report(session_summary: Dict[str, Any], settings: Dict[str, Any], strategy_name: str = '当前') -> None:
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
            annual_return = session_summary.get('annual_return', 0)
            annual_return_in_trading_days = session_summary.get('annual_return_in_trading_days', 0)
            # ROI 显示：从小数格式（0.0026）转换为百分比格式（0.26%）
            avg_roi = session_summary.get('avg_roi', 0) * 100.0

            if win_rate >= 50:
                win_rate_dot = IconService.get('green_dot')
            else:
                win_rate_dot = IconService.get('red_dot')
            print(f"{win_rate_dot} 胜率: {win_rate:.1f}%")

            if avg_roi >= 5:
                avg_roi_dot = IconService.get('green_dot')
            else:
                avg_roi_dot = IconService.get('red_dot')
            print(f"{avg_roi_dot} 平均每笔投资回报率(ROI): {avg_roi:.1f}%")

            if annual_return >= 15:
                annual_return_dot = IconService.get('green_dot')
            else:
                annual_return_dot = IconService.get('red_dot')


            if annual_return_in_trading_days >= 10:
                annual_return_in_trading_days_dot = IconService.get('green_dot')
            else:
                annual_return_in_trading_days_dot = IconService.get('red_dot')

            print(f"折算后平均每笔投资年化收益率: ")
            print(f" - {annual_return_dot} 按自然日: {annual_return:.1f}%")
            print(f" - {annual_return_in_trading_days_dot} 按交易日: {annual_return_in_trading_days:.1f}%")
            
            print(f"{IconService.get('clock')} 平均投资时长: {session_summary.get('avg_duration_in_days', 0):.1f} 自然日")
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