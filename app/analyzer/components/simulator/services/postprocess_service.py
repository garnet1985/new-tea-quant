"""
后处理服务模块

负责模拟结果的汇总、统计和报告生成
"""

from typing import Dict, List, Any, Optional, Callable
from loguru import logger
from app.analyzer.analyzer_service import AnalyzerService
from app.analyzer.components.investment import InvestmentRecorder

class PostprocessService:
    """后处理服务类"""


    @staticmethod
    def summarize_stock(simulate_result: Dict[str, Any], module_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        汇总单股票结果
        """
        stock_summary = PostprocessService.summarize_stock_by_default_way(simulate_result, module_info)

        # stock_summary = strategy_class.on_summarize_stock(stock_summary, simulate_result)

        # return stock_summary

    @staticmethod
    def summarize_stock_by_default_way(simulate_result: Dict[str, Any], module_info: Dict[str, Any]) -> Dict[str, Any]:
        import importlib
        strategy_class_name = module_info.get('strategy_class_name', '')
        strategy_module_path = module_info.get('strategy_module_path', '')
        # expose to strategy class to add any extra fields
        strategy_module = importlib.import_module(strategy_module_path)
        strategy_class = getattr(strategy_module, strategy_class_name)


        logger.info(f"simulate_result: {simulate_result}")

        stock_info = simulate_result.get('stock') or {}
        # 兼容不同阶段的字段命名：优先 settled_investments，其次 settled

        settled = simulate_result.get('settled') or []

        total = len(settled)
        success_count = 0
        fail_count = 0
        open_count = 0
        total_profit = 0.0
        total_duration = 0.0
        roi_sum_pct = 0.0
        annual_sum_pct = 0.0

        investment_records = []

        for inv in settled:
            pass

            # inv['weighted_profit'] = inv['profit'] * inv['sell_ratio']
            # overall_profit += inv['weighted_profit']

            # result = inv.get('result')
            # if result == 'win':
            #     success_count += 1
            # elif result == 'loss':
            #     fail_count += 1
            # elif result == 'open':
            #     open_count += 1

            # profit = float(inv.get('overall_profit') or 0.0)
            # total_profit += profit

            # duration_days = float(inv.get('invest_duration_days') or 0.0)
            # total_duration += duration_days

            # roi = float(inv.get('overall_profit_rate') or 0.0)
            # roi_sum_pct += roi * 100.0

            # annual_sum_pct += AnalyzerService.get_annual_return(roi, int(duration_days))

            # summarized_inv = {
            #     'result': result,
            #     'overall_profit': profit,
            #     'overall_profit_rate': roi,
            #     'invest_duration_days': duration_days,
            #     'start_date': inv.get('start_date'),
            #     'end_date': inv.get('end_date'),
            #     'purchase_price': inv.get('purchase_price'),
            #     'tracking': inv.get('tracking'),
            #     'completed_targets': inv.get('targets', {}).get('completed', []),
            # }

            # summarized_inv = strategy_class.on_summarize_stock_investment(summarized_inv, inv, stock_info)

            # investment_records.append(summarized_inv)

            # logger.info(f"investment_records: {summarized_inv}, inv: {inv}")




        # avg_profit = AnalyzerService.to_ratio(total_profit, total)
        # avg_duration_days = AnalyzerService.to_ratio(total_duration, total)
        # avg_roi = AnalyzerService.to_ratio(roi_sum_pct, total)
        # avg_annual_return = AnalyzerService.to_ratio(annual_sum_pct, total)

        # # HL 输出的胜率按总投资数计算（包含 open）
        # win_rate = AnalyzerService.to_ratio(success_count, total, 3)

        # summary = {
        #     'total_investments': total,
        #     'success_count': success_count,
        #     'fail_count': fail_count,
        #     'open_count': open_count,
        #     'win_rate': round(win_rate, 1),
        #     'total_profit': round(total_profit, 2),
        #     'avg_profit': round(avg_profit, 2),
        #     'avg_duration_days': round(avg_duration_days, 1),
        #     'avg_roi': round(avg_roi, 2),
        #     'avg_annual_return': round(avg_annual_return, 2),
        # }

        # summarized_stock = {
        #     'stock_info': stock_info,
        #     'investments': investment_records,
        #     'summary': summary,
        # }

        # summarized_stock = strategy_class.on_summarize_stock(summarized_stock, simulate_result)


        # return summarized_stock



    # @staticmethod
    # def summarize_stock_by_default_way(simulate_result: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     默认的股票汇总逻辑
        
    #     计算：
    #     - 投资成功率
    #     - 平均ROI
    #     - 平均年化收益
    #     - 平均投资周期
    #     - 盈利、亏损、微盈、微亏的比例
        
    #     Args:
    #         result: 单股票模拟结果
            
    #     Returns:
    #         Dict: 股票汇总信息
    #     """
    #     investments = simulate_result.get('investments', [])
    #     settled_investments = simulate_result.get('settled_investments', [])
        
    #     # 基本统计
    #     total_investments = len(settled_investments)
    #     current_investments = len(investments)
        
    #     if total_investments == 0:
    #         return {
    #             'total_investments': 0,
    #             'current_investments': current_investments,
    #             'win_rate': 0.0,
    #             'avg_roi': 0.0,
    #             'avg_annual_return': 0.0,
    #             'avg_duration_days': 0.0,
    #             'profit_ratio': 0.0,
    #             'loss_ratio': 0.0,
    #             'small_profit_ratio': 0.0,
    #             'small_loss_ratio': 0.0,
    #             'win_count': 0,
    #             'loss_count': 0,
    #             'small_profit_count': 0,
    #             'small_loss_count': 0
    #         }
        
    #     # 统计各种结果
    #     win_count = 0
    #     loss_count = 0
    #     small_profit_count = 0
    #     small_loss_count = 0
        
    #     total_roi = 0.0
    #     total_duration_days = 0.0
        
    #     for investment in settled_investments:
    #         result_type = investment.get('result', '')
    #         profit_rate = investment.get('overall_profit_rate', 0.0)
    #         duration_days = investment.get('invest_duration_days', 0)
            
    #         # 累计ROI和投资周期
    #         total_roi += profit_rate
    #         total_duration_days += duration_days
            
    #         # 分类统计
    #         if result_type == 'win':
    #             if profit_rate >= 0.2:  # 20%以上为盈利
    #                 win_count += 1
    #             else:  # 20%以下为微盈
    #                 small_profit_count += 1
    #         elif result_type == 'loss':
    #             if profit_rate <= -0.2:  # -20%以下为亏损
    #                 loss_count += 1
    #             else:  # -20%以上为微亏
    #                 small_loss_count += 1
        
    #     # 计算平均值
    #     avg_roi = AnalyzerService.to_ratio(total_roi, total_investments)
    #     avg_duration_days = AnalyzerService.to_ratio(total_duration_days, total_investments)
        
    #     # 计算年化收益率 - 使用原来的逻辑：基于平均ROI和平均投资周期
    #     avg_annual_return = AnalyzerService.get_annual_return(avg_roi, int(avg_duration_days))
        
    #     # 计算成功率
    #     win_rate = AnalyzerService.to_ratio(win_count + small_profit_count, total_investments)
        
    #     # 计算各种比例
    #     profit_ratio = AnalyzerService.to_ratio(win_count, total_investments)
    #     loss_ratio = AnalyzerService.to_ratio(loss_count, total_investments)
    #     small_profit_ratio = AnalyzerService.to_ratio(small_profit_count, total_investments)
    #     small_loss_ratio = AnalyzerService.to_ratio(small_loss_count, total_investments)
        
    #     return {
    #         'total_investments': total_investments,
    #         'current_investments': current_investments,
    #         'win_rate': win_rate,
    #         'avg_roi': avg_roi,
    #         'avg_annual_return': avg_annual_return,
    #         'avg_duration_days': avg_duration_days,
    #         'profit_ratio': profit_ratio,
    #         'loss_ratio': loss_ratio,
    #         'small_profit_ratio': small_profit_ratio,
    #         'small_loss_ratio': small_loss_ratio,
    #         'win_count': win_count,
    #         'loss_count': loss_count,
    #         'small_profit_count': small_profit_count,
    #         'small_loss_count': small_loss_count
    #     }

    # @staticmethod
    # def to_stock_summary(simulate_result: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     生成与 HL/tmp/524 输出一致的单股汇总结构：
    #     { 'stock_id': str, 'summary': { ...metrics... } }
    #     不依赖 EntityBuilder。
    #     """
    #     stock = simulate_result.get('stock') or {}
    #     stock_id = stock.get('id', '')
    #     summary = PostprocessService.summarize_stock_by_default_way(simulate_result)
    #     return {
    #         'stock_id': stock_id,
    #         'summary': summary,
    #     }
    
    @staticmethod
    def summarize_session(stock_summaries: List[Dict[str, Any]], 
                         on_session_summary: Optional[Callable] = None) -> Dict[str, Any]:
        """
        汇总整个会话结果
        
        Args:
            stock_summaries: 股票汇总结果列表
            on_session_summary: 用户自定义的会话汇总函数
            
        Returns:
            Dict: 会话汇总结果
        """
        logger.info("📈 开始会话汇总...")
        
        if on_session_summary:
            try:
                session_summary = on_session_summary(stock_summaries)
                return session_summary
            except Exception as e:
                logger.error(f"❌ 会话汇总失败: {e}")
                return {'error': str(e)}
        else:
            # 默认汇总逻辑 - 聚合所有股票的统计信息
            session_summary = PostprocessService._default_session_summary(stock_summaries)
            return session_summary

    @staticmethod
    def _default_session_summary(stock_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        默认的会话汇总逻辑
        
        Args:
            stock_summaries: 股票汇总结果列表
            
        Returns:
            Dict: 会话汇总结果
        """
        total_investments = 0
        current_investments = 0
        total_win_count = 0
        total_loss_count = 0
        total_small_profit_count = 0
        total_small_loss_count = 0
        
        total_roi = 0.0
        total_annual_return = 0.0
        total_duration_days = 0.0
        
        stocks_with_investments = 0
        
        for stock_summary in stock_summaries:
            summary = stock_summary.get('summary', {})
            if summary and summary.get('total_investments', 0) > 0:
                stocks_with_investments += 1
                
                total_investments += summary.get('total_investments', 0)
                current_investments += summary.get('current_investments', 0)
                
                total_win_count += summary.get('win_count', 0)
                total_loss_count += summary.get('loss_count', 0)
                total_small_profit_count += summary.get('small_profit_count', 0)
                total_small_loss_count += summary.get('small_loss_count', 0)
                
                # 加权平均计算
                stock_investments = summary.get('total_investments', 0)
                if stock_investments > 0:
                    total_roi += summary.get('avg_roi', 0) * stock_investments
                    total_annual_return += summary.get('avg_annual_return', 0) * stock_investments
                    total_duration_days += summary.get('avg_duration_days', 0) * stock_investments
        
        # 计算整体平均值
        avg_roi = (total_roi / total_investments) if total_investments > 0 else 0.0
        avg_duration_days = (total_duration_days / total_investments) if total_investments > 0 else 0.0
        
        # 对于会话级别的年化收益率，我们使用加权平均
        # 因为每只股票的年化收益率已经基于其整体表现计算
        avg_annual_return = (total_annual_return / total_investments) if total_investments > 0 else 0.0
        
        # 计算整体成功率
        total_successful = total_win_count + total_small_profit_count
        win_rate = (total_successful / total_investments * 100) if total_investments > 0 else 0.0
        
        # 计算各种比例
        profit_ratio = (total_win_count / total_investments * 100) if total_investments > 0 else 0.0
        loss_ratio = (total_loss_count / total_investments * 100) if total_investments > 0 else 0.0
        small_profit_ratio = (total_small_profit_count / total_investments * 100) if total_investments > 0 else 0.0
        small_loss_ratio = (total_small_loss_count / total_investments * 100) if total_investments > 0 else 0.0
        
        return {
            'total_investments': total_investments,
            'current_investments': current_investments,
            'total_stocks': len(stock_summaries),
            'stocks_with_investments': stocks_with_investments,
            'win_rate': win_rate,
            'avg_roi': avg_roi,
            'avg_annual_return': avg_annual_return,
            'avg_duration_days': avg_duration_days,
            'profit_ratio': profit_ratio,
            'loss_ratio': loss_ratio,
            'small_profit_ratio': small_profit_ratio,
            'small_loss_ratio': small_loss_ratio,
            'win_count': total_win_count,
            'loss_count': total_loss_count,
            'small_profit_count': total_small_profit_count,
            'small_loss_count': total_small_loss_count
        }
    
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