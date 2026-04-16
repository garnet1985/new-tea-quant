#!/usr/bin/env python3
"""
Statistics Helper - 统计助手

职责：
- 计算 Summary 统计
- 生成回测报告
"""

from typing import List, Dict, Any
import logging

from core.modules.strategy.enums import OpportunityStatus

logger = logging.getLogger(__name__)


class StatisticsHelper:
    """统计助手"""
    
    @staticmethod
    def calculate_summary(opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算机会汇总统计
        
        Args:
            opportunities: 机会列表
        
        Returns:
            summary: {
                'total_opportunities': 10,
                'total_closed': 8,
                'win_rate': 0.65,
                'avg_price_return': 0.05,
                ...
            }
        """
        if not opportunities:
            return {}
        
        closed_opps = [o for o in opportunities if o.get('status') == OpportunityStatus.CLOSED.value]
        
        summary = {
            'total_opportunities': len(opportunities),
            'total_closed': len(closed_opps)
        }
        
        if closed_opps:
            # 胜率
            wins = sum(1 for o in closed_opps if o.get('price_return', 0) > 0)
            summary['win_rate'] = wins / len(closed_opps)
            
            # 平均收益率
            summary['avg_price_return'] = sum(o.get('price_return', 0) for o in closed_opps) / len(closed_opps)
            
            # 平均持有天数
            summary['avg_holding_days'] = sum(o.get('holding_days', 0) for o in closed_opps) / len(closed_opps)
            
            # 最大收益
            summary['max_return'] = max(o.get('price_return', 0) for o in closed_opps)
            
            # 最大亏损
            summary['max_loss'] = min(o.get('price_return', 0) for o in closed_opps)
            
            # 年化收益率（假设 250 个交易日）
            if summary['avg_holding_days'] > 0:
                summary['annual_return'] = summary['avg_price_return'] * (250 / summary['avg_holding_days'])
        
        return summary
    
    @staticmethod
    def generate_scan_summary(
        strategy_name: str,
        date: str,
        strategy_version: str,
        total_stocks: int,
        opportunities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成扫描汇总"""
        summary = {
            'scan_date': date,
            'strategy_name': strategy_name,
            'strategy_version': strategy_version,
            'total_stocks_scanned': total_stocks,
            'total_opportunities_found': len(opportunities),
            'opportunity_rate': len(opportunities) / total_stocks if total_stocks else 0,
        }
        
        if opportunities:
            summary['avg_expected_return'] = sum(o.get('expected_return', 0) for o in opportunities) / len(opportunities)
            summary['avg_confidence'] = sum(o.get('confidence', 0) for o in opportunities) / len(opportunities)
        
        return summary
    
    @staticmethod
    def generate_simulate_summary(
        strategy_name: str,
        session_id: str,
        opportunities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """生成模拟汇总"""
        from datetime import datetime
        
        closed_opps = [o for o in opportunities if o.get('status') == OpportunityStatus.CLOSED.value]
        
        summary = {
            'session_id': session_id,
            'session_date': datetime.now().strftime('%Y-%m-%d'),
            'strategy_name': strategy_name,
            'total_opportunities': len(opportunities),
            'total_closed': len(closed_opps),
        }
        
        if closed_opps:
            summary['win_rate'] = sum(1 for o in closed_opps if o.get('price_return', 0) > 0) / len(closed_opps)
            summary['avg_price_return'] = sum(o.get('price_return', 0) for o in closed_opps) / len(closed_opps)
            summary['avg_holding_days'] = sum(o.get('holding_days', 0) for o in closed_opps) / len(closed_opps)
        
        return summary
