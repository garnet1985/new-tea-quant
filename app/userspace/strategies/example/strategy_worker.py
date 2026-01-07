#!/usr/bin/env python3
"""
Example Strategy Worker - 示例策略

这是一个简单的示例策略，展示如何使用新架构。

用户只需实现 scan_opportunity() 方法来定义买入信号。
框架会根据 settings.goal 配置自动执行回测（止盈止损等）。
"""

from app.core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from app.core.modules.strategy.models.opportunity import Opportunity
from typing import Optional
import uuid
from datetime import datetime


class ExampleStrategyWorker(BaseStrategyWorker):
    """
    示例策略 Worker
    
    策略逻辑：
    - 如果最新收盘价突破 20 日均线，则发现买入机会
    """
    
    def scan_opportunity(self) -> Optional[Opportunity]:
        """
        扫描投资机会
        
        用户只需实现此方法，定义买入信号逻辑。
        框架会自动处理回测（根据 settings.goal 配置）。
        
        Returns:
            Opportunity: 如果发现买入信号
            None: 如果没有发现机会
        """
        # 1. 获取 K-line 数据
        klines = self.data_manager.get_klines()
        
        if len(klines) < 20:
            return None  # 数据不足
        
        # 2. 计算 20 日均线
        ma20 = sum(k['close'] for k in klines[-20:]) / 20
        latest_price = klines[-1]['close']
        
        # 3. 判断买入条件：价格突破均线
        price_above_ma = (latest_price - ma20) / ma20
        
        if price_above_ma > 0:  # 价格高于均线
            # 发现买入机会！
            return Opportunity(
                opportunity_id=str(uuid.uuid4()),
                stock_id=self.stock_id,
                stock_name=klines[-1].get('name', ''),
                strategy_name=self.strategy_name,
                strategy_version='1.0',
                scan_date=datetime.now().strftime('%Y%m%d'),
                trigger_date=klines[-1]['date'],
                trigger_price=latest_price,
                trigger_conditions={
                    'ma20': ma20,
                    'price_above_ma': price_above_ma,
                    'signal': 'price_breakout_ma20'
                },
                expected_return=0.10,  # 预期 10% 收益
                confidence=0.70,  # 70% 置信度
                status='active',
                config_hash=str(hash(str(self.settings.to_dict()))),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
        
        return None  # 不满足买入条件
    
    # =========================================================================
    # 注意：不需要实现 simulate_opportunity() 方法！
    # 框架会根据 settings.goal 配置自动执行回测：
    # - 分段止盈止损
    # - 动态止损
    # - 保本止损
    # - 到期平仓
    # =========================================================================
