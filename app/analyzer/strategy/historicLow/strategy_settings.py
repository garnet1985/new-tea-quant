


strategy_settings = {

    # 日线数据要求
    "daily_data_requirements": {
        "freeze_period_days": 100, 
        "low_points_ref_years": [3, 5, 8],     # 冻结期：100个交易日
        "min_required_daily_records": 2000,  # 最小日线记录数
    },

    # 投资目标
    "goal": {
        "stop_loss": {
            "stages": [
                {
                    "win_ratio": 0,
                    "is_dynamic_loss": False,
                    "loss_ratio": 0.2
                },
                {
                    "win_ratio": 0.1,
                    "is_dynamic_loss": False,
                    "loss_ratio": 0
                },
                {
                    "win_ratio": 0.4,
                    "is_dynamic_loss": True,
                    "loss_ratio": 0.1  # 动态止损比例（10%）
                }
            ]
        },
        "take_profit": {
            "stages": [
                {
                    "win_ratio": 0.1,
                    "sell_ratio": 0.2
                },
                {
                    "win_ratio": 0.2,
                    "sell_ratio": 0.2
                },
                {
                    "win_ratio": 0.3,
                    "sell_ratio": 0.2
                },
                {
                    "win_ratio": 0.4,
                    "sell_ratio": 0.2
                }
            ]
        }
    },

    "low_point_invest_range": {
        # when to invest: the price is reached range of low point up and down [base] percent range
        # e.g. low point is 2, so the invest range is 2 * (1 - [base]) ~ 2 * (1 + [base])
        "base": 0.05,
        # if the invest range is less than [min]元, use [min]元 as the min range
        "min": 0.2,
        # if the invest range is greater than [max]元, use [max]元 as the max range
        "max": 10.0
    }
}