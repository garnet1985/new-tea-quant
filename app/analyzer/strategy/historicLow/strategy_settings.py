


# 策略启用状态
enabled = True

invest_settings = {
    "goal": {
        "win": 1.4,  # 40% profit
        "loss": 0.8,  # 20% loss
        "opportunityRange": 0.07,
        "kellyCriterionDivider": 5,
        "invest_reference_day_distance_threshold": 90
    },
    "terms": [60, 96],  # 保留月数信息（用于显示）
    "min_required_monthly_records": 100,
    
    # 新增：日线数据要求
    "daily_data_requirements": {
        "freeze_period_days": 200,      # 冻结期：200个交易日
        "history_periods": [
            {"name": "5year", "trading_days": 1200, "description": "5年回溯"},
            {"name": "8year", "trading_days": 2000, "description": "8年回溯"}
        ],
        "min_required_daily_records": 2000  # 最小日线记录数（同时作为总需求）
    },

    "simulate": {
        "max_workers": 5,
        # if too large wll cause db connection pool exhausted
        "batch_size": 50,
        "enable_monitoring": False
    }
}