#!/usr/bin/env python3
"""
Random Strategy Worker - 随机策略（用于测试）

这是一个用于测试的随机策略，使用固定随机种子保证结果可复现。

策略逻辑：
- 使用随机数生成器（带种子）决定是否发现买入机会
- 配置 random_seed 参数控制随机性
- 配置 probability 参数控制发现机会的概率
"""

from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.models.opportunity import Opportunity
from typing import Optional, Dict, Any
import random


class StrategyWorker(BaseStrategyWorker):
    """
    随机策略 Worker
    
    策略逻辑：
    - 根据配置的随机种子和概率，随机决定是否发现买入机会
    - 保证结果可复现（相同种子产生相同结果）
    """
    
    def scan_opportunity(self, data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Opportunity]:
        """
        扫描投资机会（随机策略）
        
        Args:
            data: 数据字典，包含：
                - data['klines']: List[Dict] - K线数据
                - data.get('tags', []): List[Dict] - 标签数据（如果配置了）
                - data.get('corporate_finance', []): List[Dict] - 财务数据（如果配置了）
                - data.get('macro', {}): Dict - 宏观数据（如果配置了）
            settings: 策略配置字典
        
        Returns:
            Opportunity: 如果随机决定发现买入信号
            None: 如果没有发现机会
        """
        from typing import Dict, Any
        
        # 1. 获取配置参数（从 settings 参数中获取）
        core_config = settings.get('core', {})
        random_seed = core_config.get('random_seed', 42)
        probability = core_config.get('probability', 0.1)  # 默认 10% 概率
        
        # 2. 从 data 参数中获取 K-line 数据（避免 IO 操作）
        klines = data.get('klines', [])
        
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
            # 注意：使用 Worker 预加载的完整股票信息（包含 id, name, industry, type, exchange_center）
            return Opportunity(
                stock=self.stock_info,  # 使用 Worker 预加载的完整股票信息
                record_of_today=latest_kline,
                extra_fields={
                    'random_seed': random_seed,
                    'combined_seed': combined_seed,
                    'probability': probability,
                    'random_value': rng.random(),
                    'signal': 'random_signal'
                }
            )
        
        return None  # 不满足买入条件（随机决定不买入）
    
    # =========================================================================
    # 注意：不需要实现 simulate_opportunity() 方法！
    # 框架会根据 settings.goal 配置自动执行回测
    # =========================================================================
