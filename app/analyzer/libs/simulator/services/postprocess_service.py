"""
后处理服务模块

负责模拟结果的汇总、统计和报告生成
"""

from typing import Dict, List, Any, Optional, Callable
from loguru import logger
from app.analyzer.analyzer_service import AnalyzerService


class PostprocessService:
    """后处理服务类"""
    
    @staticmethod
    def summarize_stocks(simulate_results: List[Dict[str, Any]], 
                        on_single_stock_summary: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        汇总单股票结果
        
        逻辑：
        1. 先执行默认汇总逻辑（投资成功率、平均ROI、平均年化收益、平均投资周期等）
        2. 如果用户提供了自定义汇总函数，则调用它来添加额外的track值到默认summary中
        
        Args:
            simulate_results: 模拟结果列表
            on_single_stock_summary: 可选的单股票汇总回调函数，用于添加额外的track值
            
        Returns:
            List[Dict]: 股票汇总结果列表
        """
        
        stock_summaries = []
        for result in simulate_results:
            stock_id = result.get('stock_id', 'unknown')
            
            # 先执行默认汇总逻辑
            summary = PostprocessService._default_stock_summary(result)
            
            # 如果用户提供了自定义汇总函数，则调用它来添加额外的track值
            if on_single_stock_summary:
                try:
                    additional_tracks = on_single_stock_summary(result)
                    if additional_tracks:
                        # 将用户自定义的track值合并到默认summary中
                        summary.update(additional_tracks)
                except Exception as e:
                    logger.error(f"❌ 股票 {stock_id} 自定义汇总失败: {e}")
                    # 即使自定义汇总失败，也保留默认summary
            
            stock_summaries.append({
                'stock_id': stock_id,
                'summary': summary
            })
        
        return stock_summaries

    @staticmethod
    def _default_stock_summary(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        默认的股票汇总逻辑
        
        计算：
        - 投资成功率
        - 平均ROI
        - 平均年化收益
        - 平均投资周期
        - 盈利、亏损、微盈、微亏的比例
        
        Args:
            result: 单股票模拟结果
            
        Returns:
            Dict: 股票汇总信息
        """
        investments = result.get('investments', [])
        settled_investments = result.get('settled_investments', [])
        
        # 基本统计
        total_investments = len(settled_investments)
        current_investments = len(investments)
        
        if total_investments == 0:
            return {
                'total_investments': 0,
                'current_investments': current_investments,
                'win_rate': 0.0,
                'avg_roi': 0.0,
                'avg_annual_return': 0.0,
                'avg_duration_days': 0.0,
                'profit_ratio': 0.0,
                'loss_ratio': 0.0,
                'small_profit_ratio': 0.0,
                'small_loss_ratio': 0.0,
                'win_count': 0,
                'loss_count': 0,
                'small_profit_count': 0,
                'small_loss_count': 0
            }
        
        # 统计各种结果
        win_count = 0
        loss_count = 0
        small_profit_count = 0
        small_loss_count = 0
        
        total_roi = 0.0
        total_duration_days = 0.0
        
        for investment in settled_investments:
            result_type = investment.get('result', '')
            profit_rate = investment.get('overall_profit_rate', 0.0)
            duration_days = investment.get('invest_duration_days', 0)
            
            # 累计ROI和投资周期
            total_roi += profit_rate
            total_duration_days += duration_days
            
            # 分类统计
            if result_type == 'win':
                if profit_rate >= 0.2:  # 20%以上为盈利
                    win_count += 1
                else:  # 20%以下为微盈
                    small_profit_count += 1
            elif result_type == 'loss':
                if profit_rate <= -0.2:  # -20%以下为亏损
                    loss_count += 1
                else:  # -20%以上为微亏
                    small_loss_count += 1
        
        # 计算平均值
        avg_roi = (total_roi / total_investments * 100) if total_investments > 0 else 0.0
        avg_duration_days = (total_duration_days / total_investments) if total_investments > 0 else 0.0
        
        # 计算年化收益率 - 使用原来的逻辑：基于平均ROI和平均投资周期
        avg_annual_return = AnalyzerService.get_annual_return(total_roi / total_investments, int(avg_duration_days)) if total_investments > 0 and avg_duration_days > 0 else 0.0
        
        # 计算成功率
        win_rate = ((win_count + small_profit_count) / total_investments * 100) if total_investments > 0 else 0.0
        
        # 计算各种比例
        profit_ratio = (win_count / total_investments * 100) if total_investments > 0 else 0.0
        loss_ratio = (loss_count / total_investments * 100) if total_investments > 0 else 0.0
        small_profit_ratio = (small_profit_count / total_investments * 100) if total_investments > 0 else 0.0
        small_loss_ratio = (small_loss_count / total_investments * 100) if total_investments > 0 else 0.0
        
        return {
            'total_investments': total_investments,
            'current_investments': current_investments,
            'win_rate': win_rate,
            'avg_roi': avg_roi,
            'avg_annual_return': avg_annual_return,
            'avg_duration_days': avg_duration_days,
            'profit_ratio': profit_ratio,
            'loss_ratio': loss_ratio,
            'small_profit_ratio': small_profit_ratio,
            'small_loss_ratio': small_loss_ratio,
            'win_count': win_count,
            'loss_count': loss_count,
            'small_profit_count': small_profit_count,
            'small_loss_count': small_loss_count
        }
    
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
    def generate_final_report(simulate_results: List[Dict[str, Any]], 
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
        
        # 调用用户自定义的完成回调函数
        if on_simulate_complete:
            try:
                on_simulate_complete(final_report)
            except Exception as e:
                logger.error(f"❌ 完成回调执行失败: {e}")
        
        return final_report
