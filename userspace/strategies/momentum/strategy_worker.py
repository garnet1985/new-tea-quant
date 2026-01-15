#!/usr/bin/env python3
"""
Momentum Strategy Worker - 动量策略

策略逻辑：
- 计算最近 20 天和之前 40 天的平均价格
- 如果动量 > 阈值，则发现买入机会
- 回测时，检查止盈止损
"""

from core.modules.strategy.base_strategy_worker import BaseStrategyWorker
from core.modules.strategy.models.opportunity import Opportunity
from typing import Optional, Dict, Any


class MomentumStrategyWorker(BaseStrategyWorker):
    """动量策略 Worker"""
    
    def scan_opportunity(self, data: Dict[str, Any], settings: Dict[str, Any]) -> Optional[Opportunity]:
        """
        扫描动量机会
        
        逻辑：
        1. 获取最新 60 天的 K-line
        2. 计算动量 = (最近20天均价 - 之前40天均价) / 之前40天均价
        3. 如果动量 > 阈值，返回 Opportunity
        
        Args:
            data: 数据字典，包含：
                - data['klines']: List[Dict] - K线数据（已包含技术指标）
                - data.get('tags', []): List[Dict] - 标签数据（如果配置了）
                - data.get('corporate_finance', []): List[Dict] - 财务数据（如果配置了）
                - data.get('macro', {}): Dict - 宏观数据（如果配置了）
            settings: 策略配置字典
        """
        from typing import Dict, Any
        
        # 1. 从 data 参数中获取 K-line 数据（避免 IO 操作）
        klines = data.get('klines', [])
        
        if len(klines) < 60:
            return None  # 数据不足
        
        # 2. 计算动量
        recent_20 = klines[-20:]
        prev_40 = klines[-60:-20]
        
        recent_avg = sum(k['close'] for k in recent_20) / 20
        prev_avg = sum(k['close'] for k in prev_40) / 40
        
        momentum = (recent_avg - prev_avg) / prev_avg
        
        # 3. 判断是否满足条件（从 settings 参数中获取）
        core_config = settings.get('core', {})
        momentum_threshold = core_config.get('momentum_threshold', 0.05)
        
        if momentum > momentum_threshold:
            # 发现机会！
            # 注意：使用 Worker 预加载的完整股票信息（包含 id, name, industry, type, exchange_center）
            latest_kline = klines[-1]
            return Opportunity(
                stock=self.stock_info,  # 使用 Worker 预加载的完整股票信息
                record_of_today=latest_kline,
                extra_fields={
                    'momentum': momentum,
                    'recent_avg': recent_avg,
                    'prev_avg': prev_avg
                }
            )
        
        return None  # 不满足条件
    
    def simulate_opportunity(self, opportunity: Opportunity) -> Opportunity:
        """
        回测动量机会
        
        逻辑：
        1. 找到买入日期
        2. 遍历持有期，检查止盈止损
        3. 计算收益率
        4. 更新 Opportunity
        """
        # 1. 获取历史数据
        klines = self.data_manager.get_klines()
        
        if not klines:
            logger.error(f"没有 K-line 数据: {self.stock_id}")
            return opportunity
        
        # 2. 找到买入日期的索引
        buy_index = None
        for i, k in enumerate(klines):
            if k['date'] == opportunity.trigger_date:
                buy_index = i
                break
        
        if buy_index is None:
            logger.error(f"找不到触发日期: {opportunity.trigger_date}")
            return opportunity
        
        buy_price = opportunity.trigger_price
        
        # 3. 遍历持有期
        sell_date = None
        sell_price = None
        sell_reason = None
        max_price = buy_price
        min_price = buy_price
        tracking_prices = [buy_price]
        tracking_returns = [0]
        holding_days = 0
        
        stop_loss = self.settings.execution.stop_loss
        take_profit = self.settings.execution.take_profit
        max_holding_days = self.settings.execution.max_holding_days
        
        for i in range(buy_index + 1, len(klines)):
            current_kline = klines[i]
            current_price = current_kline['close']
            holding_days = i - buy_index
            
            # 追踪
            tracking_prices.append(current_price)
            tracking_returns.append((current_price - buy_price) / buy_price)
            
            max_price = max(max_price, current_price)
            min_price = min(min_price, current_price)
            
            # 计算价格收益率
            price_return = (current_price - buy_price) / buy_price
            
            # 止损
            if price_return <= stop_loss:
                sell_date = current_kline['date']
                sell_price = current_price
                sell_reason = 'stop_loss'
                break
            
            # 止盈
            if price_return >= take_profit:
                sell_date = current_kline['date']
                sell_price = current_price
                sell_reason = 'take_profit'
                break
            
            # 最大持有期
            if holding_days >= max_holding_days:
                sell_date = current_kline['date']
                sell_price = current_price
                sell_reason = 'max_holding'
                break
        
        # 4. 如果没有触发，最后一天卖出
        if not sell_date:
            sell_date = klines[-1]['date']
            sell_price = klines[-1]['close']
            sell_reason = 'end_of_period'
            holding_days = len(klines) - 1 - buy_index
        
        # 5. 更新 Opportunity
        opportunity.sell_date = sell_date
        opportunity.sell_price = sell_price
        opportunity.sell_reason = sell_reason
        opportunity.price_return = (sell_price - buy_price) / buy_price
        opportunity.holding_days = holding_days
        opportunity.max_price = max_price
        opportunity.min_price = min_price
        opportunity.max_drawdown = (min_price - buy_price) / buy_price
        
        # 持有期追踪
        opportunity.tracking = {
            'daily_prices': tracking_prices,
            'daily_returns': tracking_returns,
            'max_reached_date': klines[buy_index + tracking_prices.index(max_price)]['date'] if tracking_prices else '',
            'min_reached_date': klines[buy_index + tracking_prices.index(min_price)]['date'] if tracking_prices else ''
        }
        
        opportunity.status = 'closed'
        opportunity.updated_at = datetime.now().isoformat()
        
        return opportunity
