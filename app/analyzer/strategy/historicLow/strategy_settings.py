


# 策略启用状态
enabled = True

invest_settings = {
    "goal": {
        "win": 1.4,  # 40% profit
        "loss": 0.8,  # 20% loss
        "opportunityRange": 0.07,
        "kellyCriterionDivider": 5
    },

    
    # 新增：日线数据要求
    "daily_data_requirements": {
        "freeze_period_days": 50,       # 冻结期：50个交易日（缩小，覆盖更多历史数据）
        "history_periods": [
            {"name": "5year", "trading_days": 1200, "description": "5年回溯"},
            {"name": "8year", "trading_days": 2000, "description": "8年回溯"},
            {"name": "10year", "trading_days": 2500, "description": "10年回溯"}
        ],
        "min_required_daily_records": 2000,  # 最小日线记录数（同时作为总需求）
        
        # 新增：波谷检测配置
        "valley_detection": {
            "min_drop_threshold": 0.10,    # 最小跌幅阈值（10%）
            "local_range_days": 5,         # 局部最低点判断范围（前后5天）
            "lookback_days": 60            # 寻找前期高点的回溯天数（60天）
        }
    },

    "simulate": {
        "max_workers": 5,
        # if too large wll cause db connection pool exhausted
        "batch_size": 50,
        "enable_monitoring": False
    }
}