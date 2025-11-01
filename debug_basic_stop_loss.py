#!/usr/bin/env python3
"""
调试基础止损止盈逻辑
"""

from app.analyzer.components.base_strategy import BaseStrategy
from app.analyzer.components.investment.investment_goal_manager import InvestmentGoalManager

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

# 模拟交易记录
record_of_today = {'close': 100.0, 'date': '20231001'}
stock_info = {'id': '000001', 'name': '测试股票'}

# 创建opportunity
opportunity = BaseStrategy.create_opportunity(
    stock=stock_info,
    record_of_today=record_of_today,
)

print("1. Opportunity created:")
print(f"   price: {opportunity['price']}")
print(f"   date: {opportunity['date']}")

# 创建投资
investment = BaseStrategy.create_investment(record_of_today, opportunity, settings)

print("\n2. Investment created:")
print(f"   purchase_price: {investment['purchase_price']}")

print("\n3. Targets created:")
stop_loss_targets = investment['targets_tracking']['stop_loss']['targets']
take_profit_targets = investment['targets_tracking']['take_profit']['targets']

for target in stop_loss_targets:
    print(f"   止损目标: {target['name']} - target_price: {target['target_price']}, ratio: {target['ratio']}")

for target in take_profit_targets:
    print(f"   止盈目标: {target['name']} - target_price: {target['target_price']}, ratio: {target['ratio']}")

# 模拟价格变化，测试目标触发
print("\n4. Testing target triggering:")

test_prices = [50.0, 70.0, 85.0, 100.0, 130.0, 150.0]

for price in test_prices:
    test_record = {'close': price, 'date': '20231002'}

    print(f"\n   Price: {price}")

    # 测试止损
    for target in stop_loss_targets:
        is_triggered = InvestmentGoalManager._check_target_completion(test_record, target, investment)
        print(f"     止损 {target['name']}: {'✅' if is_triggered else '❌'} (target: {target['target_price']})")

    # 测试止盈
    for target in take_profit_targets:
        is_triggered = InvestmentGoalManager._check_target_completion(test_record, target, investment)
        print(f"     止盈 {target['name']}: {'✅' if is_triggered else '❌'} (target: {target['target_price']})")

    # 重置目标状态（因为目标一旦触发就会被标记为is_achieved）
    for target in stop_loss_targets + take_profit_targets:
        if 'is_achieved' in target:
            target['is_achieved'] = False
