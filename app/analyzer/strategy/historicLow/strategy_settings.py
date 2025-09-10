


strategy_settings = {

    # 测试模式配置
    "test_mode": {
        "test_problematic_stocks_only": False,  # 是否专门测试问题股票
        "max_test_stocks": None,  # 最大测试股票数量
    },

    # 日线数据要求
    "daily_data_requirements": {
        "freeze_period_days": 100,           # 冻结期：100个交易日
        "low_points_ref_years": [2, 4, 6, 8],     
        "max_invest_slope": -0.1,  # 对应约-5度的价格变化率
        "min_required_daily_records": 2000,  # 最小日线记录数
    },

    # 投资目标
    "goal": {
        "stop_loss": {
            "stages": [
                {
                    "name": "loss20%",
                    "ratio": -0.2,
                    "close_invest": True  # 止损时：清仓
                },
                {
                    "name": "break_even",
                    "ratio": 0,
                    "close_invest": True  # 止损时：清仓
                },
                {
                    "name": "dynamic",
                    "ratio": -0.1,
                    "close_invest": True  # 动态止损时：清仓
                }
            ]
        },
        "take_profit": {
            "stages": [
                {
                    "name": "win10%",
                    "ratio": 0.1,
                    "sell_ratio": 0.2,  # 止盈时：卖出总仓位的20%
                    "set_stop_loss": "break_even"
                },
                {
                    "name": "win20%",
                    "ratio": 0.2,
                    "sell_ratio": 0.2  # 止盈时：卖出总仓位的20%
                },
                {
                    "name": "win30%",
                    "ratio": 0.3,
                    "sell_ratio": 0.2  # 止盈时：卖出总仓位的20%
                },
                {
                    "name": "win40%",
                    "ratio": 0.4,
                    "sell_ratio": 0.2,  # 止盈时：卖出总仓位的20%
                    "set_stop_loss": "dynamic"
                }
            ]
        }
    },

    "low_point_invest_range": {
        # when to invest: the price is reached range of low point up and down [base] percent range
        # e.g. low point is 2, so the invest range is 2 * (1 - [base]) ~ 2 * (1 + [base])
        "upper_bound": 0.1,
        "lower_bound": 0.05,
        # if the invest range is less than [min]元, use [min]元 as the min range
        "min": 0.2,
        # if the invest range is greater than [max]元, use [max]元 as the max range
        "max": 10.0,
        # 最大触底次数限制：冻结期内触及投资点超过此次数就不再投资
        "max_touch_times": 2
    },
    # 波段完成过滤（参考低点后需完成“谷->峰->回撤”）
    "wave_filter": {
        "min_rise_ratio": 0.30,        # 谷->峰 最小涨幅
        "min_retrace_ratio": 0.10,     # 峰->回撤 最小回撤
        "max_window_days": 756         # 最大窗口（约3年交易日）
    },

    "slope_check": {
        # 检查近期股价斜率是否过于陡峭下跌
        "enabled": True,  # 是否启用斜率检查
        "days": 5,  # 检查的天数
        "max_slope_degrees": -45.0  # 最大允许的斜率角度（度），负值表示下跌
    },

    "amplitude_filter": {
        # 振幅过滤配置
        "min_amplitude": 0.10,  # 最小振幅阈值，默认10%
        "description": "过滤掉冻结期内振幅小于阈值的投资机会"
    },

    "kelly_formula": {
        # 凯莉公式配置
        "enabled": True,  # 是否启用凯莉公式
        "min_capital_threshold": 200000,  # 最小资金阈值，超过此金额使用凯莉公式
        "base_shares": 500,  # 基础股数（固定投资时使用）
        "min_kelly_fraction": 0.05,  # 最小凯莉投资比例（5%）
        "max_kelly_fraction": 0.30,  # 最大凯莉投资比例（30%）
        "default_win_rate": 0.5,  # 默认胜率（无历史数据时）
        "default_avg_win": 0.15,  # 默认平均盈利（15%）
        "default_avg_loss": -0.08,  # 默认平均亏损（-8%）
        "description": "凯莉公式配置：资金超过20万时自动使用凯莉公式进行仓位管理"
    },

    "investment_filter": {
        # 投资机会过滤配置
        "enabled": True,  # 是否启用投资过滤
        "min_capital_threshold": 500000,  # 资金小于此金额时启用过滤
        "min_roi_threshold": 0.05,  # 最小收益率阈值（5%）
        "description": "资金小于50万时，只投资预期收益率大于5%的机会"
    },

    # 问题股票列表 - 基于422版本测试结果重新定义
    "problematic_stocks": {
        "list": [
            "000546.SZ",
            "000547.SZ",
            "000599.SZ",
            "000663.SZ",
            "000790.SZ",
            "000815.SZ",
            "000878.SZ",
            "000890.SZ",
            "000911.SZ",
            "000953.SZ",
            "000980.SZ",
            "002023.SZ",
            "002026.SZ",
            "002073.SZ",
            "002106.SZ",
            "002175.SZ",
            "002196.SZ",
            "002264.SZ",
            "002307.SZ",
            "002427.SZ",
            "002439.SZ",
            "002488.SZ",
            "300013.SZ",
            "300047.SZ",
            "300081.SZ",
            "300123.SZ",
            "300150.SZ",
            "300183.SZ",
            "300221.SZ",
            "300234.SZ",
            "300244.SZ",
            "300256.SZ",
            "300258.SZ",
            "300263.SZ",
            "300265.SZ",
            "300277.SZ",
            "600159.SH",
            "600178.SH",
            "600192.SH",
            "600241.SH",
            "600319.SH",
            "600418.SH",
            "600423.SH",
            "600510.SH",
            "600539.SH",
            "600550.SH",
            "600769.SH",
            "600770.SH",
            "600791.SH",
            "600818.SH",
            "601111.SH"
        ],
        "count": 51,  # 问题股票总数
        "description": "基于最新模拟结果自动更新的黑名单"
    }
}