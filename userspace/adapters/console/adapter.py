#!/usr/bin/env python3
"""
Console Adapter - 控制台输出适配器

职责：
- 在控制台打印扫描结果
- 显示机会信息 + 历史胜率统计
"""

from typing import List, Dict, Any

from core.modules.adapter import BaseOpportunityAdapter
from core.modules.strategy.models.opportunity import Opportunity


class ConsoleAdapter(BaseOpportunityAdapter):
    """控制台输出适配器"""
    
    def process(
        self,
        opportunities: List[Opportunity],
        context: Dict[str, Any]
    ) -> None:
        """
        在控制台打印机会信息
        
        Args:
            opportunities: 机会列表
            context: 上下文信息
        """
        if not opportunities:
            self.log_info("没有发现任何机会")
            return
        
        date = context.get('date', 'unknown')
        strategy_name = context.get('strategy_name', 'unknown')
        summary = context.get('scan_summary', {})
        
        # 打印标题
        print("\n" + "=" * 80)
        print(f"📊 扫描结果 - {strategy_name}")
        print("=" * 80)
        print(f"扫描日期: {date}")
        print(f"发现机会: {len(opportunities)} 个")
        print(f"涉及股票: {summary.get('total_stocks', 0)} 只")
        print("=" * 80)
        
        # 打印每个机会
        for i, opp in enumerate(opportunities, 1):
            print(f"\n【机会 {i}】")
            print(f"  股票: {opp.stock_name} ({opp.stock_id})")
            print(f"  触发日期: {opp.trigger_date}")
            print(f"  触发价格: {opp.trigger_price:.2f}")
            
            # 打印额外信息（如果有）
            if opp.extra_fields:
                print(f"  额外信息: {opp.extra_fields}")
        
        print("\n" + "=" * 80)
        
        # 历史胜率统计（如果配置启用）
        show_history = self.get_config('show_history', True)
        if show_history and opportunities:
            self._print_history_statistics(opportunities, strategy_name)
        
        print("\n" + "=" * 80)
    
    def _print_history_statistics(
        self,
        opportunities: List[Opportunity],
        strategy_name: str
    ) -> None:
        """
        打印历史胜率统计
        
        Args:
            opportunities: 机会列表
            strategy_name: 策略名称
        """
        from core.modules.adapter.history_loader import HistoryLoader
        
        print("\n📊 历史统计信息")
        print("-" * 80)
        
        # 加载会话汇总（整体统计）
        session_summary = HistoryLoader.load_session_summary(strategy_name)
        if session_summary:
            # win_rate 已经是百分比格式（0-100，来自 to_percent），avg_roi 是小数格式（0-1）
            win_rate = session_summary.get('win_rate', 0)
            avg_roi = session_summary.get('avg_roi', 0) * 100  # 转换为百分比
            
            total_investments = session_summary.get('total_investments', 0)
            total_win = session_summary.get('total_win_investments', 0)
            total_loss = session_summary.get('total_loss_investments', 0)
            
            print(f"整体表现:")
            if total_investments > 0:
                print(f"  总投资次数: {total_investments} (盈利: {total_win}, 亏损: {total_loss})")
                print(f"  胜率: {win_rate:.1f}%")
                print(f"  平均收益率: {avg_roi:.2f}%")
                
                # 显示年化收益率（如果有）
                annual_return = session_summary.get('annual_return', 0)
                if annual_return:
                    print(f"  年化收益率: {annual_return:.2f}%")
            else:
                print(f"  暂无历史投资记录")
        
        # 按股票统计
        stock_stats = {}
        for opp in opportunities:
            stock_id = opp.stock_id
            if stock_id not in stock_stats:
                history = HistoryLoader.load_stock_history(strategy_name, stock_id)
                if history:
                    stock_stats[stock_id] = {
                        'stock_name': opp.stock_name,
                        'history': history
                    }
        
        if stock_stats:
            print(f"\n按股票统计（共 {len(stock_stats)} 只）:")
            for stock_id, stats in stock_stats.items():
                history = stats['history']
                stock_name = stats['stock_name']
                
                win_rate = history.get('win_rate', 0)
                avg_return = history.get('avg_return', 0)
                completed = history.get('completed_investments', 0)
                win_count = history.get('win_count', 0)
                loss_count = history.get('loss_count', 0)
                
                # 转换为百分比显示
                win_rate_pct = win_rate * 100
                avg_return_pct = avg_return * 100
                
                # 图标
                win_icon = "✅" if win_rate >= 0.5 else "⚠️"
                return_icon = "📈" if avg_return > 0 else "📉"
                
                print(f"  {win_icon} {stock_name} ({stock_id}):")
                print(f"    完成投资: {completed} 次 (盈利: {win_count}, 亏损: {loss_count})")
                print(f"    {return_icon} 胜率: {win_rate_pct:.1f}%, 平均收益: {avg_return_pct:.2f}%")
                
                # 显示最大/最小收益（如果有意义）
                max_return = history.get('max_return', 0)
                min_return = history.get('min_return', 0)
                if max_return != 0 or min_return != 0:
                    print(f"    收益区间: {min_return*100:.2f}% ~ {max_return*100:.2f}%")
