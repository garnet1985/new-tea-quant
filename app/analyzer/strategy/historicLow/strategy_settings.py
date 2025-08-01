


# 策略启用状态
enabled = True

invest_settings = {
    "goal": {
        "win": 1.5,  # 50% profit
        "loss": 0.8,  # 20% loss
        "opportunityRange": 0.05,
        "kellyCriterionDivider": 5
    },
    # 区间：整个月线的25%，40%，70%位置
    "dividers": [0.3, 0.5],
    "min_required_monthly_records": 100
}