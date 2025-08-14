


# 策略启用状态
enabled = True

invest_settings = {
    "goal": {
        "win": 1.5,  # 50% profit
        "loss": 0.8,  # 20% loss
        "opportunityRange": 0.1,
        "kellyCriterionDivider": 5,
        "invest_reference_day_distance_threshold": 90
    },
    "terms": [60, 96],  # 60个月和96个月的历史低点，0表示全历史（在代码中单独处理）
    # 区间：整个月线的25%，40%，70%位置
    # "dividers": [0.3, 0.5],
    "min_required_monthly_records": 100,

    "simulate": {
        "max_workers": 5,
        # if too large wll cause db connection pool exhausted
        "batch_size": 50,
        "enable_monitoring": False
    }
}