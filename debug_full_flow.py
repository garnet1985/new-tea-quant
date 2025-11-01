#!/usr/bin/env python3
"""
调试完整的simulator流程
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

# 模拟交易记录序列（股价从100开始，然后下跌）
trading_records = [
    {'close': 100.0, 'date': '20231001'},  # 开仓日
    {'close': 95.0, 'date': '20231002'},   # 跌5%
    {'close': 90.0, 'date': '20231003'},   # 跌10%
    {'close': 85.0, 'date': '20231004'},   # 跌15%
    {'close': 80.0, 'date': '20231005'},   # 跌20%
    {'close': 75.0, 'date': '20231006'},   # 跌25%
    {'close': 70.0, 'date': '20231007'},   # 跌30% - 应该触发止损
    {'close': 65.0, 'date': '20231008'},   # 继续下跌
]

stock_info = {'id': '000001', 'name': '测试股票'}

# 模拟第一天：创建投资
record_day1 = trading_records[0]
opportunity = BaseStrategy.create_opportunity(
    stock=stock_info,
    record_of_today=record_day1,
)

investment = BaseStrategy.create_investment(record_day1, opportunity, settings)

print("投资创建完成:")
print(f"  买入价格: {investment['purchase_price']}")
print(f"  止损目标: {investment['targets_tracking']['stop_loss']['targets'][0]['target_price']}")
print(f"  止盈目标: {investment['targets_tracking']['take_profit']['targets'][0]['target_price']}")

# 模拟后续交易日
for i, record in enumerate(trading_records[1:], 1):
    print(f"\n第{i+1}天 - 价格: {record['close']} (日期: {record['date']})")

    # 检查投资是否结算
    is_settled, settled_investment = InvestmentGoalManager.is_investment_settled(
        record, investment, {}, settings, BaseStrategy
    )

    if is_settled:
        print("  🎯 止损止盈触发！投资结算")
        print(f"  结算价格: {record['close']}")
        roi = (record['close'] - investment['purchase_price']) / investment['purchase_price'] * 100
        print(f"  ROI: {roi:.2f}%")
        break
    else:
        print("  ❌ 未触发，继续持有")

print("\n最终状态:")
print(f"  剩余仓位比例: {investment['targets_tracking']['investment_ratio_left']}")
print(f"  已完成目标数量: {len(investment['targets_tracking']['completed'])}")
for completed in investment['targets_tracking']['completed']:
    print(f"    - {completed['name']}: 卖出价格 {completed.get('sell_price', 'N/A')}")
