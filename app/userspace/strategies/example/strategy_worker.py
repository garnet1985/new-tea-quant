#!/usr/bin/env python3
"""
Example Strategy Worker - 示例策略

这是一个简单的示例策略，展示如何使用新架构。

用户只需实现 scan_opportunity() 方法来定义买入信号。
框架会根据 settings.goal 配置自动执行回测（止盈止损等）。
"""

from app.core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from app.core.modules.strategy.models.opportunity import Opportunity
from typing import Optional, Dict, Any
from loguru import logger


class ExampleStrategyWorker(BaseStrategyWorker):
    """
    示例策略 Worker
    
    策略逻辑：
    - 当最新 RSI(14) 低于阈值（默认 35）时认为超卖，产生买入机会
    - 使用固定随机种子保证结果可复现（主要用于 opportunity_id）
    """
    
    def scan_opportunity(self, data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Opportunity]:
        """
        扫描投资机会
        
        用户只需实现此方法，定义买入信号逻辑。
        框架会自动处理回测（根据 settings.goal 配置）。
        
        Args:
            data: 数据字典，包含：
                - data['klines']: List[Dict] - K线数据（已包含技术指标，如 ma5, rsi14 等）
                - data.get('tags', []): List[Dict] - 标签数据（如果配置了 required_entities）
                - data.get('corporate_finance', []): List[Dict] - 财务数据（如果配置了）
                - data.get('macro', {}): Dict - 宏观数据（如果配置了）
            settings: 策略配置字典，包含：
                - settings['core']: Dict - 核心配置（如 random_seed, rsi_length 等）
                - settings['data']: Dict - 数据配置
                - settings['simulator']: Dict - 模拟器配置
                - settings['goal']: Dict - 止盈止损配置
        
        Returns:
            Opportunity: 如果发现买入信号
            None: 如果没有发现机会
        """
        # 1. 获取配置参数（从 settings 参数中获取）
        core_config = settings.get('core', {})
        data_config = settings.get('data', {})
        indicators_cfg = (data_config.get('indicators') or {}).get('rsi') or []

        # RSI 周期仅从 indicators 中读取，避免与 core 重复配置
        if indicators_cfg and isinstance(indicators_cfg, list):
            rsi_length = int(indicators_cfg[0].get('period', 14))
        else:
            rsi_length = 14

        # 超卖阈值仍然放在 core 中
        rsi_threshold = core_config.get('rsi_oversold_threshold', 35)
        
        # 2. 从 data 参数中获取 K-line 数据（避免 IO 操作）
        klines = data.get('klines', [])
        if not klines or len(klines) < rsi_length:
            return None  # 数据不足，无法计算 RSI
        
        # 3. 获取最新 K 线（K 线数据已包含技术指标，直接从字段中读取）
        latest_kline = klines[-1]
        
        # 4. 从 K 线中读取 RSI 值（指标已在数据准备阶段计算并写入）
        rsi_field = f'rsi{rsi_length}'
        latest_rsi = latest_kline.get(rsi_field)

        # 如果 RSI 字段不存在，说明指标计算失败，返回 None
        if latest_rsi is None:
            return None
        
        # 5. 判断买入条件：RSI 低于超卖阈值（例如 35）
        if latest_rsi >= rsi_threshold:
            return None
        
        # 5. 发现买入机会！
        # 注意：不需要手动构建 stock_info，框架会自动使用 Worker 预加载的完整股票信息
        # 如果用户提供了 stock，会与预加载的信息合并；如果没提供，框架会自动使用预加载的信息
        return Opportunity(
            stock=self.stock_info,  # 使用 Worker 预加载的完整股票信息
            record_of_today=latest_kline,
            extra_fields={
                'rsi_value': latest_rsi,
            }
        )
    
    # =========================================================================
    # 注意：不需要实现 simulate_opportunity() 方法！
    # 框架会根据 settings.goal 配置自动执行回测：
    # - 分段止盈止损
    # - 动态止损
    # - 保本止损
    # - 到期平仓
    # =========================================================================
