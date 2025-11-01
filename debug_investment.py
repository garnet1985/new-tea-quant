#!/usr/bin/env python3
"""
调试投资创建和目标检查
"""

from app.analyzer.components.base_strategy import BaseStrategy
from app.analyzer.strategy.Random.Random import RandomStrategy

# 模拟Random策略的settings
settings = {
    "goal": {
        "stop_loss": {
            "stages": [
                {
                    "name": "loss30%",
                    "ratio": -0.3,
                    "close_invest": True
                }
            ]
        },
        "take_profit": {
            "stages": [
                {
                    "name": "win30%",
                    "ratio": 0.3,
                    "close_invest": True
                }
            ]
        },
    },
}

# 模拟数据
record_of_today = {'close': 100.0, 'date': '20231001'}
stock_info = {'id': '000001', 'name': '测试股票'}

# 模拟20天的数据来计算amplitude_delta
klines = []
for i in range(21):
    klines.append({
        'close': 100.0,
        'highest': 105.0,
        'lowest': 95.0
    })

# 计算动态止损止盈
amplitude_delta = RandomStrategy._calculate_amplitude_delta(klines, 20)
stop_loss_ratio = RandomStrategy._get_stop_loss_ratio(record_of_today, amplitude_delta or 0.05)
take_profit_ratio = RandomStrategy._get_take_profit_ratio(stop_loss_ratio, {'core': {'profit_loss_ratio': 1.5}})

print("动态计算的结果:")
print(f"amplitude_delta: {amplitude_delta}")
print(f"stop_loss_ratio: {stop_loss_ratio}")
print(f"take_profit_ratio: {take_profit_ratio}")

# 创建opportunity
opportunity = BaseStrategy.create_opportunity(
    stock=stock_info,
    record_of_today=record_of_today,
    extra_fields={
        'stop_loss': stop_loss_ratio,
        'take_profit': take_profit_ratio,
        'amplitude_delta': amplitude_delta,
    },
)

print(f"\nOpportunity extra_fields: {opportunity.get('extra_fields')}")

# 创建投资
investment = BaseStrategy.create_investment(record_of_today, opportunity, settings)

print("\n投资目标:")
print(f"止损目标: {investment['targets_tracking']['stop_loss']['targets'][0]}")
print(f"止盈目标: {investment['targets_tracking']['take_profit']['targets'][0]}")

# 测试目标检查
from app.analyzer.components.investment.investment_goal_manager import InvestmentGoalManager

test_prices = [95.0, 100.0, 107.5, 110.0]
for price in test_prices:
    test_record = {'close': price, 'date': '20231002'}

    print(f"\n测试价格: {price}")

    # 检查止损
    stop_loss_targets = investment['targets_tracking']['stop_loss']['targets']
    for target in stop_loss_targets:
        is_triggered = InvestmentGoalManager._check_target_completion(test_record, target, investment)
        print(f"  止损目标 {target['name']}: {'✅触发' if is_triggered else '❌未触发'}")

    # 检查止盈
    take_profit_targets = investment['targets_tracking']['take_profit']['targets']
    for target in take_profit_targets:
        is_triggered = InvestmentGoalManager._check_target_completion(test_record, target, investment)
        print(f"  止盈目标 {target['name']}: {'✅触发' if is_triggered else '❌未触发'}")
