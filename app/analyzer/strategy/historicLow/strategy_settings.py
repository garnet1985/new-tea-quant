


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
            # === 基于422版本测试结果，胜率≤50%或平均收益≤0%的股票 ===
            "000701.SZ",  # 厦门信达 - 基于422结果
            "000816.SZ",  # 智慧农业 - 基于422结果
            "000856.SZ",  # 冀东装备 - 基于422结果
            "002041.SZ",  # 登海种业 - 基于422结果
            "002144.SZ",  # 宏达高科 - 基于422结果
            "002249.SZ",  # 大洋电机 - 基于422结果
            "002623.SZ",  # 亚玛顿 - 基于422结果
            "300183.SZ",  # 东软载波 - 基于422结果
            "600082.SH",  # 海泰发展 - 基于422结果
            "600121.SH",  # 郑州煤电 - 基于422结果
            "600287.SH",  # 江苏舜天 - 基于422结果
            "600307.SH",  # 酒钢宏兴 - 基于422结果
            "600616.SH",  # 金枫酒业 - 基于422结果
            "600744.SH",  # 华银电力 - 基于422结果
            "600819.SH",  # 耀皮玻璃 - 基于422结果
        ],
        "count": 15,  # 问题股票总数
        "description": "基于422版本测试结果重新定义的黑名单，胜率≤50%或平均收益≤0%的股票"
    }
}