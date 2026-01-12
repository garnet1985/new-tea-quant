"""
后处理服务模块

负责模拟结果的汇总、统计和报告生成
"""

from typing import Dict, List, Any
from loguru import logger
from app.core.modules.analyzer.analyzer_service import AnalyzerService
from app.core.modules.analyzer.enums import InvestmentResult
from app.core.utils.icon.icon_service import IconService

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

        total_investments = len(settled)
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
            total_duration += inv['duration_in_days']   
            # ROI 统一标准：内部存储为小数（0.20 = 20%），显示时转换为百分比
            total_roi += inv['roi']

            # 盈亏分类：使用小数比较（0.2 = 20%）
            if inv['roi'] >= 0.2:
                profitable_count += 1
            elif inv['roi'] >= 0 and inv['roi'] < 0.2:
                minor_profitable_count += 1
            elif inv['roi'] < 0 and inv['roi'] > -0.2:
                minor_unprofitable_count += 1
            else:
                unprofitable_count += 1

            investment_data = {
                'result': result,

                'start_date': inv['start_date'],
                'end_date': inv['end_date'],
                'purchase_price': inv['purchase_price'],
                'duration_in_days': inv['duration_in_days'],

                'overall_profit': inv['overall_profit'],
                'roi': inv['roi'],
                'overall_annual_return': AnalyzerService.get_annual_return(inv['roi'], inv['duration_in_days']),
                
                'tracking': inv.get('amplitude_tracking', {}),

                'completed_targets': inv.get('completed_targets', []),
            }
            
            # 只在有 extra_fields 时才添加
            if 'extra_fields' in inv and inv['extra_fields']:
                investment_data['extra_fields'] = inv['extra_fields']
            
            investments.append(investment_data)

        avg_profit = AnalyzerService.to_ratio(total_profit, total_investments)
        avg_duration_in_days = AnalyzerService.to_ratio(total_duration, total_investments)
        avg_roi = AnalyzerService.to_ratio(total_roi, total_investments)
        
        annual_return_raw = AnalyzerService.get_annual_return(avg_roi, avg_duration_in_days)
        annual_return = float(annual_return_raw.real) if isinstance(annual_return_raw, complex) else float(annual_return_raw) if isinstance(annual_return_raw, (int, float)) else 0.0
        annual_return_in_trading_days_raw = AnalyzerService.get_annual_return(avg_roi, avg_duration_in_days, is_trading_days=True)
        annual_return_in_trading_days = float(annual_return_in_trading_days_raw.real) if isinstance(annual_return_in_trading_days_raw, complex) else float(annual_return_in_trading_days_raw) if isinstance(annual_return_in_trading_days_raw, (int, float)) else 0.0

        win_rate = AnalyzerService.to_ratio((profitable_count + minor_profitable_count), total_investments, 3)

        summary = {
            'total_investments': total_investments,
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
    def summarize_session(stock_summaries: List[Dict[str, Any]], strategy_class: Any, settings: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        汇总整个会话结果
        
        Args:
            stock_summaries: 股票汇总结果列表
            strategy_class: 策略类
            settings: 策略设置
            
        Returns:
            Dict: 会话汇总结果
        """
        base_session_summary = PostprocessService.summarize_session_by_default_way(stock_summaries)

        session_summary = strategy_class.on_summarize_session(base_session_summary, stock_summaries, settings)

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

                # 加权平均计算
                stock_avg_roi = summary.get('avg_roi', 0)
                stock_roi_contribution = stock_avg_roi * investment_count
                total_roi += stock_roi_contribution
                total_duration_days += summary.get('avg_duration_in_days', 0) * investment_count
        
        # 计算整体平均值 - avg_roi 需要更高精度（4位小数）以避免小ROI被舍入为0
        avg_roi = AnalyzerService.to_ratio(total_roi, total_investments, decimals=4)
        avg_duration_days = AnalyzerService.to_ratio(total_duration_days, total_investments)
        
        # 使用"平均ROI + 平均持有期"推导会话级平均年化，更稳健
        annual_return_raw = AnalyzerService.get_annual_return(avg_roi, avg_duration_days)
        annual_return = float(annual_return_raw.real) if isinstance(annual_return_raw, complex) else float(annual_return_raw) if isinstance(annual_return_raw, (int, float)) else 0.0
        annual_return_in_trading_days_raw = AnalyzerService.get_annual_return(avg_roi, avg_duration_days, is_trading_days=True)
        annual_return_in_trading_days = float(annual_return_in_trading_days_raw.real) if isinstance(annual_return_in_trading_days_raw, complex) else float(annual_return_in_trading_days_raw) if isinstance(annual_return_in_trading_days_raw, (int, float)) else 0.0
        
        # 计算整体成功率
        win_rate = AnalyzerService.to_percent(total_win, total_investments)
        
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

            'stocks_have_opportunities': stocks_with_opportunities,
        }

        # 添加ROI分布统计和投资时长分布统计
        roi_distribution = PostprocessService._calculate_roi_distribution(stock_summaries)
        duration_distribution = PostprocessService._calculate_duration_distribution(stock_summaries)
        
        # 将新统计信息添加到summary中
        default_session_summary.update(roi_distribution)
        default_session_summary.update(duration_distribution)
        
        return default_session_summary
    
    @staticmethod
    def present_session_report(session_summary: Dict[str, Any], settings: Dict[str, Any], strategy_name: str = '当前', module_info: Dict[str, Any] = None) -> None:
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

            if annual_return >= 0.15:
                annual_return_dot = IconService.get('green_dot')
            else:
                annual_return_dot = IconService.get('red_dot')


            if annual_return_in_trading_days >= 0.1:
                annual_return_in_trading_days_dot = IconService.get('green_dot')
            else:
                annual_return_in_trading_days_dot = IconService.get('red_dot')

            print(f"折算后平均每笔投资年化收益率: ")
            print(f" - {annual_return_dot} 按自然日: {annual_return * 100:.1f}%")
            print(f" - {annual_return_in_trading_days_dot} 按交易日: {annual_return_in_trading_days * 100:.1f}%")
            
            print(f"{IconService.get('clock')} 平均投资时长: {session_summary.get('avg_duration_in_days', 0):.1f} 自然日")
            print(f"{IconService.get('bar_chart')} 总投资次数: {session_summary.get('total_investments', 0)}")
            print(f"{IconService.get('success')} 成功次数: {session_summary.get('total_win_investments', 0)}")
            print(f"{IconService.get('error')} 失败次数: {session_summary.get('total_loss_investments', 0)}")
            print(f"{IconService.get('ongoing')} 未完成次数: {session_summary.get('total_open_investments', 0)}")
            print("")
            print("📈 ROI分布统计:")
            print(f" - 平均ROI: {session_summary.get('roi_mean', 0)*100:.1f}%")
            print(f" - 中位数ROI: {session_summary.get('roi_median', 0)*100:.1f}%")
            print(f" - 25分位数: {session_summary.get('roi_25th_percentile', 0)*100:.1f}%")
            print(f" - 75分位数: {session_summary.get('roi_75th_percentile', 0)*100:.1f}%")
            print(f" - 标准差: {session_summary.get('roi_std', 0)*100:.1f}%")
            print(f" - 最小ROI: {session_summary.get('roi_min', 0)*100:.1f}%")
            print(f" - 最大ROI: {session_summary.get('roi_max', 0)*100:.1f}%")

            print("")
        print("📊 ROI区间分布:")
        total_inv = session_summary.get('total_investments', 0)
        if total_inv > 0:
            print(f" - <-10%: {session_summary.get('roi_lt_10pct', 0)}次 ({session_summary.get('roi_lt_10pct', 0)/total_inv*100:.1f}%)")
            print(f" - -10%~-5%: {session_summary.get('roi_10_to_5pct', 0)}次 ({session_summary.get('roi_10_to_5pct', 0)/total_inv*100:.1f}%)")
            print(f" - -5%~0%: {session_summary.get('roi_5_to_0pct', 0)}次 ({session_summary.get('roi_5_to_0pct', 0)/total_inv*100:.1f}%)")
            print(f" - 0%~5%: {session_summary.get('roi_0_to_5pct', 0)}次 ({session_summary.get('roi_0_to_5pct', 0)/total_inv*100:.1f}%)")
            print(f" - 5%~10%: {session_summary.get('roi_5_to_10pct', 0)}次 ({session_summary.get('roi_5_to_10pct', 0)/total_inv*100:.1f}%)")
            print(f" - 10%~15%: {session_summary.get('roi_10_to_15pct', 0)}次 ({session_summary.get('roi_10_to_15pct', 0)/total_inv*100:.1f}%)")
            print(f" - 15%~20%: {session_summary.get('roi_15_to_20pct', 0)}次 ({session_summary.get('roi_15_to_20pct', 0)/total_inv*100:.1f}%)")
            print(f" - 20%~30%: {session_summary.get('roi_20_to_30pct', 0)}次 ({session_summary.get('roi_20_to_30pct', 0)/total_inv*100:.1f}%)")
            print(f" - 30%~50%: {session_summary.get('roi_30_to_50pct', 0)}次 ({session_summary.get('roi_30_to_50pct', 0)/total_inv*100:.1f}%)")
            print(f" - >50%: {session_summary.get('roi_gt_50pct', 0)}次 ({session_summary.get('roi_gt_50pct', 0)/total_inv*100:.1f}%)")
        else:
            print(" - 无投资记录")
        print("")
        print("📅 投资时长分布:")
        print(f" - 平均时长: {session_summary.get('duration_mean', 0):.1f}天")
        print(f" - 中位数时长: {session_summary.get('duration_median', 0):.1f}天")
        print(f" - 标准差: {session_summary.get('duration_std', 0):.1f}天")
        print(f" - 最短时长: {session_summary.get('duration_min', 0):.0f}天")
        print(f" - 最长时长: {session_summary.get('duration_max', 0):.0f}天")
        print(f" - 25分位数: {session_summary.get('duration_25th_percentile', 0):.1f}天")
        print(f" - 75分位数: {session_summary.get('duration_75th_percentile', 0):.1f}天")
        print("")
        print("📊 投资时长区间分布:")
        total_duration = session_summary.get('total_investments', 0)
        if total_duration > 0:
            print(f" - 1-5天: {session_summary.get('duration_1_to_5_days', 0)}次 ({session_summary.get('duration_1_to_5_days', 0)/total_duration*100:.1f}%)")
            print(f" - 6-10天: {session_summary.get('duration_6_to_10_days', 0)}次 ({session_summary.get('duration_6_to_10_days', 0)/total_duration*100:.1f}%)")
            print(f" - 11-20天: {session_summary.get('duration_11_to_20_days', 0)}次 ({session_summary.get('duration_11_to_20_days', 0)/total_duration*100:.1f}%)")
            print(f" - 21-30天: {session_summary.get('duration_21_to_30_days', 0)}次 ({session_summary.get('duration_21_to_30_days', 0)/total_duration*100:.1f}%)")
            print(f" - 31-60天: {session_summary.get('duration_31_to_60_days', 0)}次 ({session_summary.get('duration_31_to_60_days', 0)/total_duration*100:.1f}%)")
            print(f" - 61-90天: {session_summary.get('duration_61_to_90_days', 0)}次 ({session_summary.get('duration_61_to_90_days', 0)/total_duration*100:.1f}%)")
            print(f" - 91-180天: {session_summary.get('duration_91_to_180_days', 0)}次 ({session_summary.get('duration_91_to_180_days', 0)/total_duration*100:.1f}%)")
            print(f" - >180天: {session_summary.get('duration_gt_180_days', 0)}次 ({session_summary.get('duration_gt_180_days', 0)/total_duration*100:.1f}%)")
        else:
            print(" - 无投资记录")
        print("="*60)
        
        # 调用策略的扩展报告方法

        import importlib
        strategy_module_path = module_info.get('strategy_module_path', '')
        strategy_class_name = module_info.get('strategy_class_name', '')
        
        strategy_module = importlib.import_module(strategy_module_path)
        strategy_class = getattr(strategy_module, strategy_class_name)
            
        # 调用策略的扩展报告方法
        if hasattr(strategy_class, 'present_extra_session_report'):
            strategy_class.present_extra_session_report(session_summary, settings)

        # 检查是否需要自动分析
        if settings.get('simulation', {}).get('analysis', False):
            PostprocessService._run_auto_analysis(session_summary, settings, strategy_name, module_info)
    
    @staticmethod
    def _run_auto_analysis(session_summary: Dict[str, Any], settings: Dict[str, Any], strategy_name: str, module_info: Dict[str, Any] = None) -> None:
        """
        自动运行分析并保存结果到文件
        
        Args:
            session_summary: 会话汇总数据
            settings: 策略设置
            strategy_name: 策略名称
        """
        try:
            import importlib
            import os
            
            if not module_info:
                logger.warning(f"⚠️ 未提供模块信息，跳过自动分析")
                return
            
            # 从module_info中获取策略模块信息
            strategy_module_path = module_info.get('strategy_module_path', '')
            strategy_class_name = module_info.get('strategy_class_name', '')
            strategy_folder_name = module_info.get('strategy_folder_name', '')
            
            if not all([strategy_module_path, strategy_class_name, strategy_folder_name]):
                logger.warning(f"⚠️ 无法获取策略模块信息，跳过自动分析")
                return
            
            # 导入策略类
            strategy_module = importlib.import_module(strategy_module_path)
            strategy_class = getattr(strategy_module, strategy_class_name)
            
            # 创建策略实例
            strategy_instance = strategy_class()
            
            # 运行分析
            analysis_result = strategy_instance.analysis()
            
            # 保存分析结果到文件
            PostprocessService._save_analysis_to_file(strategy_folder_name, analysis_result)
            
        except Exception as e:
            logger.error(f"❌ 自动分析失败: {e}")
            import traceback
            traceback.print_exc()

    @staticmethod
    def _save_analysis_to_file(strategy_folder_name: str, analysis_result: Dict[str, Any]) -> None:
        """
        将分析结果保存到文件
        
        Args:
            strategy_folder_name: 策略文件夹名称
            analysis_result: 分析结果
        """
        try:
            import json
            import os
            
            # 构建tmp目录路径
            tmp_dir = f"app/analyzer/strategy/{strategy_folder_name}/tmp"
            
            # 获取最新的会话目录
            if os.path.exists(tmp_dir):
                session_dirs = [d for d in os.listdir(tmp_dir) if os.path.isdir(os.path.join(tmp_dir, d))]
                if session_dirs:
                    # 按时间排序，获取最新的
                    latest_session_dir = sorted(session_dirs)[-1]
                    analysis_file_path = os.path.join(tmp_dir, latest_session_dir, "0_session_analysis.json")
                    
                    # 确保目录存在
                    os.makedirs(os.path.dirname(analysis_file_path), exist_ok=True)
                    
                    # 保存分析结果
                    with open(analysis_file_path, 'w', encoding='utf-8') as f:
                        json.dump(analysis_result, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"📝 分析结果已保存: {analysis_file_path}")
                else:
                    logger.warning(f"⚠️ 未找到会话目录，无法保存分析结果")
            else:
                logger.warning(f"⚠️ tmp目录不存在: {tmp_dir}")
                
        except Exception as e:
            logger.error(f"❌ 保存分析结果失败: {e}")
            import traceback
            traceback.print_exc()
    
    @staticmethod
    def _calculate_roi_distribution(stock_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算ROI分布统计
        
        Returns:
            Dict[str, Any]: ROI分布统计字典
        """
        import numpy as np
        
        all_rois = []
        
        # 收集所有投资的ROI
        for stock_summary in stock_summaries:
            investments = stock_summary.get('investments', [])
            
            for investment in investments:
                roi = investment.get('roi', 0)
                all_rois.append(roi)
        
        if not all_rois:
            return {}
        
        # 计算ROI分布统计
        roi_stats = {
            'roi_mean': np.mean(all_rois),
            'roi_median': np.median(all_rois),
            'roi_std': np.std(all_rois),
            'roi_min': np.min(all_rois),
            'roi_max': np.max(all_rois),
            'roi_25th_percentile': np.percentile(all_rois, 25),
            'roi_75th_percentile': np.percentile(all_rois, 75),
            'roi_90th_percentile': np.percentile(all_rois, 90),
            'roi_95th_percentile': np.percentile(all_rois, 95),
        }
        
        # 计算ROI区间分布
        roi_bins = [-float('inf'), -0.1, -0.05, 0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5, float('inf')]
        roi_bin_counts, _ = np.histogram(all_rois, bins=roi_bins)
        roi_bin_labels = ['<-10%', '-10%~-5%', '-5%~0%', '0%~5%', '5%~10%', '10%~15%', '15%~20%', '20%~30%', '30%~50%', '>50%']
        
        # 使用更直观的区间命名
        roi_bin_keys = [
            'roi_lt_10pct',      # <-10%
            'roi_10_to_5pct',    # -10%~-5%
            'roi_5_to_0pct',     # -5%~0%
            'roi_0_to_5pct',     # 0%~5%
            'roi_5_to_10pct',    # 5%~10%
            'roi_10_to_15pct',   # 10%~15%
            'roi_15_to_20pct',   # 15%~20%
            'roi_20_to_30pct',   # 20%~30%
            'roi_30_to_50pct',   # 30%~50%
            'roi_gt_50pct'       # >50%
        ]
        
        roi_distribution = {}
        for i, count in enumerate(roi_bin_counts):
            roi_distribution[roi_bin_keys[i]] = int(count)
        
        roi_stats.update(roi_distribution)
        
        return roi_stats
    
    @staticmethod
    def _calculate_duration_distribution(stock_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算投资时长分布统计
        
        Returns:
            Dict: 投资时长分布统计信息
        """
        import numpy as np
        
        all_durations = []
        
        # 收集所有投资的投资时长
        for stock_summary in stock_summaries:
            investments = stock_summary.get('investments', [])
            
            for investment in investments:
                duration = investment.get('duration_in_days', 0)
                if duration >= 0:  # 统计所有投资（包括0天的投资）
                    all_durations.append(duration)
        
        if not all_durations:
            return {}
        
        # 计算时长分布统计
        duration_stats = {
            'duration_mean': float(np.mean(all_durations)),
            'duration_median': float(np.median(all_durations)),
            'duration_std': float(np.std(all_durations)),
            'duration_min': int(np.min(all_durations)),
            'duration_max': int(np.max(all_durations)),
            'duration_25th_percentile': float(np.percentile(all_durations, 25)),
            'duration_75th_percentile': float(np.percentile(all_durations, 75)),
            'duration_90th_percentile': float(np.percentile(all_durations, 90)),
            'duration_95th_percentile': float(np.percentile(all_durations, 95)),
        }
        
        # 计算时长区间分布
        duration_bins = [0, 5, 10, 20, 30, 60, 90, 180, float('inf')]
        duration_bin_counts, _ = np.histogram(all_durations, bins=duration_bins)
        
        # 使用更直观的区间命名
        duration_bin_keys = [
            'duration_1_to_5_days',     # 1-5天
            'duration_6_to_10_days',    # 6-10天
            'duration_11_to_20_days',   # 11-20天
            'duration_21_to_30_days',   # 21-30天
            'duration_31_to_60_days',   # 31-60天
            'duration_61_to_90_days',   # 61-90天
            'duration_91_to_180_days',  # 91-180天
            'duration_gt_180_days'      # >180天
        ]
        
        duration_distribution = {}
        for i, count in enumerate(duration_bin_counts):
            duration_distribution[duration_bin_keys[i]] = int(count)
        
        duration_stats.update(duration_distribution)
        
        return duration_stats
    