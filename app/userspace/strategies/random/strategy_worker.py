#!/usr/bin/env python3
"""
Random Strategy Worker - 随机策略（用于测试）

这是一个用于测试的随机策略，使用固定随机种子保证结果可复现。

策略逻辑：
- 使用随机数生成器（带种子）决定是否发现买入机会
- 配置 random_seed 参数控制随机性
- 配置 probability 参数控制发现机会的概率
"""

from app.core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from app.core.modules.strategy.models.opportunity import Opportunity
from typing import Optional
import uuid
import random
from datetime import datetime


class StrategyWorker(BaseStrategyWorker):
    """
    随机策略 Worker
    
    策略逻辑：
    - 根据配置的随机种子和概率，随机决定是否发现买入机会
    - 保证结果可复现（相同种子产生相同结果）
    """
    
    def scan_opportunity(self) -> Optional[Opportunity]:
        """
        扫描投资机会（随机策略）
        
        Returns:
            Opportunity: 如果随机决定发现买入信号
            None: 如果没有发现机会
        """
        # 1. 获取配置参数
        random_seed = self.settings.core.get('random_seed', 42)
        probability = self.settings.core.get('probability', 0.1)  # 默认 10% 概率
        
        # 2. 获取 K-line 数据（用于生成机会信息）
        klines = self.data_manager.get_klines()
        
        if not klines or len(klines) < 1:
            return None  # 数据不足
        
        # 3. 初始化随机数生成器（使用种子 + 股票代码 + 日期保证可复现且不同股票不同结果）
        latest_kline = klines[-1]
        date_str = latest_kline['date']
        # 组合种子：基础种子 + 股票代码 + 日期
        combined_seed = hash(f"{random_seed}_{self.stock_id}_{date_str}") % (2**31)
        rng = random.Random(combined_seed)
        
        # 4. 随机决定是否发现机会
        if rng.random() < probability:
            # 发现买入机会！
            return Opportunity(
                opportunity_id=str(uuid.uuid4()),
                stock_id=self.stock_id,
                stock_name=latest_kline.get('name', ''),
                strategy_name=self.strategy_name,
                strategy_version='1.0',
                scan_date=datetime.now().strftime('%Y%m%d'),
                trigger_date=latest_kline['date'],
                trigger_price=latest_kline['close'],
                trigger_conditions={
                    'random_seed': random_seed,
                    'combined_seed': combined_seed,
                    'probability': probability,
                    'random_value': rng.random(),
                    'signal': 'random_signal'
                },
                expected_return=0.05,  # 预期 5% 收益
                confidence=0.50,  # 50% 置信度（随机策略）
                status='active',
                config_hash=str(hash(str(self.settings.to_dict()))),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
        
        return None  # 不满足买入条件（随机决定不买入）
    
    # =========================================================================
    # 注意：不需要实现 simulate_opportunity() 方法！
    # 框架会根据 settings.goal 配置自动执行回测
    # =========================================================================
