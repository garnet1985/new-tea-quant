"""
后处理服务模块

负责模拟结果的汇总、统计和报告生成
"""

from typing import Dict, List, Any, Optional, Callable
from loguru import logger
from app.analyzer.analyzer_service import AnalyzerService
from app.analyzer.components.investment import InvestmentRecorder
from app.analyzer.components.enum import InvestmentResult

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
            on_session_summary: 用户自定义的会话汇总函数
            
        Returns:
            Dict: 会话汇总结果
        """
        session_summary = PostprocessService.summarize_session_by_default_way(stock_summaries)

        import importlib
        strategy_class_name = module_info.get('strategy_class_name', '')
        strategy_module_path = module_info.get('strategy_module_path', '')
        # expose to strategy class to add any extra fields
        strategy_module = importlib.import_module(strategy_module_path)
        strategy_class = getattr(strategy_module, strategy_class_name)

        session_summary = strategy_class.on_summarize_session(session_summary, stock_summaries)

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

        logger.info(f"default_session_summary: {default_session_summary}")

        return default_session_summary
    
    @staticmethod
    def generate_quick_simulate_report(simulate_results: List[Dict[str, Any]], 
                            stock_summaries: List[Dict[str, Any]], 
                            session_summary: Dict[str, Any],
                            settings: Dict[str, Any],
                            processing_time: float,
                            on_simulate_complete: Optional[Callable] = None) -> Dict[str, Any]:
        """
        生成最终报告
        
        Args:
            simulate_results: 模拟结果列表
            stock_summaries: 股票汇总结果列表
            session_summary: 会话汇总结果
            settings: 策略设置
            processing_time: 处理时间
            on_simulate_complete: 用户自定义的完成回调函数
            
        Returns:
            Dict: 最终报告
        """
        final_report = {
            'session_summary': session_summary,
            'stock_summaries': stock_summaries,
            'raw_results': simulate_results,
            'settings': settings,
            'processing_time': processing_time
        }
        
        # 检查是否需要保存投资结果
        record_summary = settings.get('mode', {}).get('record_summary', False)
        if record_summary:
            try:
                # 创建投资记录器（严格要求 folder_name）
                if 'folder_name' not in settings or not settings['folder_name']:
                    raise KeyError("settings.folder_name is required for recording results")
                folder_name = settings['folder_name']
                invest_recorder = InvestmentRecorder(folder_name)
                
                # 保存股票汇总结果
                if stock_summaries:
                    for stock_summary in stock_summaries:
                        stock_id = stock_summary['stock_id']
                        
                        # 找到对应的原始模拟结果
                        raw_result = None
                        for result in simulate_results:
                            if result.get('stock_id') == stock_id:
                                raw_result = result
                                break
                        
                        # 构建完整的数据结构，包含投资记录
                        adapted_summary = {
                            'stock_info': {'id': stock_id},
                            'summary': stock_summary['summary']
                        }
                        
                        # 添加投资记录（如果有的话）
                        if raw_result:
                            all_investments = []
                            
                            # 添加已结算的投资
                            if raw_result.get('settled_investments'):
                                all_investments.extend(raw_result['settled_investments'])
                            
                            # 添加当前投资（如果有的话）
                            if raw_result.get('investments'):
                                all_investments.extend(raw_result['investments'])
                            
                            if all_investments:
                                # 简化投资记录结构（通用部分），opportunity 留给策略在 on_single_stock_summary 中扩展
                                simplified_investments = []
                                for investment in all_investments:
                                    simplified_investment = {
                                        'result': investment.get('result'),
                                        'stock': investment.get('stock'),
                                        'start_date': investment.get('start_date'),
                                        'end_date': investment.get('end_date'),
                                        'purchase_price': investment.get('purchase_price'),
                                        'tracking': investment.get('tracking'),  # 保留tracking信息
                                        'overall_profit': investment.get('overall_profit'),
                                        'overall_profit_rate': investment.get('overall_profit_rate'),
                                        'invest_duration_days': investment.get('invest_duration_days')
                                    }
                                    # 简化targets - 只保留completed结果
                                    if investment.get('targets', {}).get('completed'):
                                        simplified_investment['targets'] = {
                                            'completed': investment['targets']['completed']
                                        }
                                    # 保留原始opportunity；策略可通过 on_single_stock_summary 增补或派生额外字段
                                    if investment.get('opportunity'):
                                        simplified_investment['opportunity'] = investment['opportunity']
                                    
                                    simplified_investments.append(simplified_investment)
                                adapted_summary['investments'] = simplified_investments
                        
                        invest_recorder.save_stock_summary(adapted_summary)
                    logger.info(f"💾 已保存 {len(stock_summaries)} 个股票汇总结果")
                
                # 保存会话汇总结果
                if session_summary:
                    invest_recorder.save_session(session_summary)
                    logger.info("💾 已保存会话汇总结果")
                
                logger.info(f"📁 投资结果已保存到: {invest_recorder.tmp_dir}")
            except Exception as e:
                logger.error(f"❌ 保存投资结果失败: {e}")
        
        # 调用用户自定义的完成回调函数
        if on_simulate_complete:
            try:
                on_simulate_complete(final_report)
            except Exception as e:
                logger.error(f"❌ 完成回调执行失败: {e}")
        
        return final_report

    @staticmethod
    def log_quick_simulate_report(final_report: Dict[str, Any]) -> None:
        """
        通用的控制台展示方法（与HL展示格式一致，可被各策略复用）
        """
        session_summary = final_report.get('session_summary', {})
        print("\n" + "="*60)
        print("📊 HistoricLow 策略回测结果汇总")
        print("="*60)
        if session_summary:
            win_rate = session_summary.get('win_rate', 0)
            avg_annual_return = session_summary.get('avg_annual_return', 0)
            win_rate_dot = "🟢" if win_rate >= 60 else "🔴"
            print(f"🎯 胜率: {win_rate_dot} {win_rate:.1f}%")
            annual_return_dot = "🟢" if avg_annual_return >= 15 else "🔴"
            print(f"📈 平均年化收益率: {annual_return_dot} {avg_annual_return:.1f}%")
            print(f"⏱️  平均投资时长: {session_summary.get('avg_duration_days', 0):.1f} 天")
            print(f"💰 平均ROI: {session_summary.get('avg_roi', 0):.1f}%")
            print(f"📊 总投资次数: {session_summary.get('total_investments', 0)}")
            print(f"✅ 成功次数: {session_summary.get('win_count', 0) + session_summary.get('small_profit_count', 0)}")
            print(f"❌ 失败次数: {session_summary.get('loss_count', 0) + session_summary.get('small_loss_count', 0)}")
            print("<------------------------------------------->")
            print(f"🟢 盈利次数: {session_summary.get('win_count', 0)} ({session_summary.get('profit_ratio', 0):.1f}%)")
            print(f"🟡 微盈次数: {session_summary.get('small_profit_count', 0)} ({session_summary.get('small_profit_ratio', 0):.1f}%)")
            print(f"🟠 微损次数: {session_summary.get('small_loss_count', 0)} ({session_summary.get('small_loss_ratio', 0):.1f}%)")
            print(f"🔴 亏损次数: {session_summary.get('loss_count', 0)} ({session_summary.get('loss_ratio', 0):.1f}%)")
            print("="*60)