"""
后处理服务模块

负责模拟结果的汇总、统计和报告生成
"""

from typing import Dict, List, Any, Optional, Callable
from loguru import logger


class PostprocessService:
    """后处理服务类"""
    
    @staticmethod
    def summarize_stocks(simulate_results: List[Dict[str, Any]], 
                        on_single_stock_summary: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        汇总单股票结果
        
        Args:
            simulate_results: 模拟结果列表
            on_single_stock_summary: 用户自定义的单股票汇总函数
            
        Returns:
            List[Dict]: 股票汇总结果列表
        """
        
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
        
        return stock_summaries
    
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
            # 默认汇总逻辑
            total_investments = 0
            total_settled = 0
            current_investments = 0
            
            for stock_summary in stock_summaries:
                summary = stock_summary.get('summary', {})
                if summary:
                    total_investments += summary.get('total_investments', 0)
                    total_settled += summary.get('total_settled', 0)
                    current_investments += summary.get('current_investments', 0)
            
            session_summary = {
                'total_investments': total_investments,
                'total_settled': total_settled,
                'current_investments': current_investments,
                'total_stocks': len(stock_summaries)
            }
            
            return session_summary
    
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
