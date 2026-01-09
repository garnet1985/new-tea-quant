#!/usr/bin/env python3
"""
Example Strategy Worker - 示例策略

这是一个简单的示例策略，展示如何使用新架构。

用户只需实现 scan_opportunity() 方法来定义买入信号。
框架会根据 settings.goal 配置自动执行回测（止盈止损等）。
"""

from app.core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from app.core.modules.strategy.models.opportunity import Opportunity
from app.core.modules.indicator.indicator_service import IndicatorService
from typing import Optional
import uuid
from datetime import datetime
import random


class ExampleStrategyWorker(BaseStrategyWorker):
    """
    示例策略 Worker
    
    策略逻辑：
    - 当最新 RSI(14) 低于阈值（默认 35）时认为超卖，产生买入机会
    - 使用固定随机种子保证结果可复现（主要用于 opportunity_id）
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
        # 1. 获取配置参数（用于保证可复现性和 RSI 阈值）
        random_seed = self.settings.core.get('random_seed', 42)
        rsi_length = self.settings.core.get('rsi_length', 14)
        rsi_threshold = self.settings.core.get('rsi_oversold_threshold', 35)
        
        # 2. 获取 K-line 数据
        klines = self.data_manager.get_klines()
        if not klines or len(klines) < rsi_length:
            return None  # 数据不足，无法计算 RSI
        
        # 3. 计算 RSI
        rsi_values = IndicatorService.rsi(klines, length=rsi_length)
        if not rsi_values or len(rsi_values) == 0:
            return None
        
        latest_kline = klines[-1]
        latest_price = latest_kline['close']
        latest_rsi = rsi_values[-1]
        
        # 4. 判断买入条件：RSI 低于超卖阈值（例如 35）
        if latest_rsi >= rsi_threshold:
            return None
        
        # 5. 使用固定种子生成 UUID（保证可复现性）
        # 组合种子：基础种子 + 股票代码 + 日期
        date_str = latest_kline['date']
        combined_seed = hash(f"{random_seed}_{self.stock_id}_{date_str}") % (2**31)
        rng = random.Random(combined_seed)
        opportunity_uuid = uuid.UUID(int=rng.getrandbits(128))
        
        # 发现买入机会！
        return Opportunity(
            opportunity_id=str(opportunity_uuid),
            stock_id=self.stock_id,
            stock_name=latest_kline.get('name', ''),
            strategy_name=self.strategy_name,
            strategy_version='1.0',
            scan_date=datetime.now().strftime('%Y%m%d'),
            trigger_date=latest_kline['date'],
            trigger_price=latest_price,
            trigger_conditions={
                'rsi_length': rsi_length,
                'rsi_value': latest_rsi,
                'rsi_oversold_threshold': rsi_threshold,
                'signal': 'rsi_oversold',
                'random_seed': random_seed,
                'combined_seed': combined_seed,
            },
            expected_return=0.10,  # 示例：预期 10% 收益
            confidence=0.50,       # 示例：50% 置信度
            status='active',
            config_hash=str(hash(str(self.settings.to_dict()))),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
    
    # =========================================================================
    # 注意：不需要实现 simulate_opportunity() 方法！
    # 框架会根据 settings.goal 配置自动执行回测：
    # - 分段止盈止损
    # - 动态止损
    # - 保本止损
    # - 到期平仓
    # =========================================================================
