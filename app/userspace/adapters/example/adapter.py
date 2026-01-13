#!/usr/bin/env python3
"""
Example Adapter - 示例适配器

这是一个示例，展示如何创建自定义 adapter。
"""

from typing import List, Dict, Any

from app.core.modules.adapter import BaseOpportunityAdapter
from app.core.modules.strategy.models.opportunity import Opportunity


class ExampleAdapter(BaseOpportunityAdapter):
    """示例适配器"""
    
    def process(
        self,
        opportunities: List[Opportunity],
        context: Dict[str, Any]
    ) -> None:
        """
        处理机会列表
        
        Args:
            opportunities: 机会列表
            context: 上下文信息
        """
        # 获取配置
        output_format = self.get_config('format', 'json')
        
        # 处理逻辑
        self.log_info(f"处理 {len(opportunities)} 个机会，格式: {output_format}")
        
        # 示例：转换为 JSON 格式
        if output_format == 'json':
            import json
            result = {
                'date': context.get('date'),
                'strategy': context.get('strategy_name'),
                'opportunities': [opp.to_dict() for opp in opportunities]
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 示例：转换为 CSV 格式
        elif output_format == 'csv':
            import csv
            import sys
            if opportunities:
                fieldnames = list(opportunities[0].to_dict().keys())
                writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
                writer.writeheader()
                for opp in opportunities:
                    writer.writerow(opp.to_dict())
