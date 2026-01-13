#!/usr/bin/env python3
"""
Console Adapter - 控制台输出适配器

职责：
- 在控制台打印扫描结果
- 显示机会信息 + 历史胜率统计
"""

from typing import List, Dict, Any

from app.core.modules.adapter import BaseOpportunityAdapter
from app.core.modules.strategy.models.opportunity import Opportunity


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
        
        # TODO: 后续可以添加历史胜率统计
        # 读取历史模拟结果，计算每只股票的胜率、平均收益等
