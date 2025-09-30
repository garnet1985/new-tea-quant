settings = {
    "core": {
        "convergence": {
            "days": 20,
        },
        "stability": {
            "days": 10,
        },
        "invest_range": {
            "lower_bound": 0.01,
            "upper_bound": 0.01,
        },
    },

    # 模拟模式
    'mode': {
        # 是不是只模拟黑名单中的股票
        "blacklist_only": False,
        # 测试股票数量
        "test_amount": 100,
        # 测试股票起始索引
        "start_idx": 1000,
        # 模拟参考版本号
        "simulation_ref_version": "",
        # 是否记录模拟结果，结果会自动存在{folder_name}的tmp文件夹下
        "record_summary" : True
    },

    # 日线数据要求
    "klines": {
        # 日线数据要求 - 例子中指代模拟需要加在日，周，月线数据，模拟器会根据这个配置自动加载数据
        "terms": ["daily", "weekly", "monthly"],
        # 日线数据要求 - 例子中指代模拟器基于日线来进行一日日的模拟（交易日）
        "base_term": "daily",
        # 最小要求的基础周期记录数
        "min_required_base_records": 100,
        # 复权方式
        "adjust": "qfq",
        # 要在K线上增加的技术指标
        "indicators": {
            "moving_average": {
                "periods": [5, 10, 20, 60],
            },
            "rsi": {
                "period": 14,  # 14日RSI
            },
        },
    },

    # 模拟时间范围 - 日期格式YYYYMMDD （例如：20080101）
    "simulation": {
        # 模拟开始日期 - 空指代2008-01-01
        "start_date": "",
        # 模拟结束日期 - 空指代到最新的记录
        "end_date": ""
    },

    # 投资目标设置
    "goal": {
        # 固定期限强制平仓（可选）：自然日 与 交易日 二选一或同时配置
        # 仅用于到期平仓，不属于止盈/止损；若配置则即便无止盈止损也会在到期时平仓
        "fixed_days": 10,
        # "fixed_trading_days": 7,

        # 是否自定义止损目标 - 如果有此属性且为true，则完全使用此属性来判断是否应该结算投资，以下属性均不生效
        'is_customized': False,
        
        # 止损目标设置
        "stop_loss": {
            # 保本止损
            "break_even": {
                "name": "break_even",
                "ratio": 0,
                # close invest 代表卖出剩余所有仓位
                "close_invest": True  # 止损时：清仓
            },
            # 动态止损（追损）
            "dynamic": {
                "name": "dynamic",
                # ratio 代表在止损设置后累计出现过的最高点的下方10%为止损值
                "ratio": -0.1,
                "close_invest": True  # 动态止损时：清仓
            },
            # 分段止损
            "stages": [
                # 止损阶段
                {
                    # 名字随便取，只负责展示
                    "name": "loss5%",
                    # 当前价格低于买入价格的20%时触发止损
                    "ratio": -0.05,
                    # 止损行为是卖出所有仓位
                    "close_invest": True  # 止损时：清仓
                }
            ]
        },
        # 止盈目标设置（超短线配置：快速止盈）
        "take_profit": {
            # 止盈阶段（按比例分批卖出）；可为空
            "stages": [
                {
                    "name": "win3%",
                    "ratio": 0.03,
                    "sell_ratio": 0.5,
                    "set_stop_loss": "break_even"
                },
                {
                    "name": "win5%",
                    "ratio": 0.05,
                    "sell_ratio": 0.5
                }
            ]
        },

        # 黑名单设置, 黑名单设置存在时 mode:blacklist_only 才会生效
        "blacklist": {
            # 黑名单数量
            "count": 0,
            "description": "avg_roi<0 (from 524)",
            # 黑名单列表
            "list": []
        }
    },
}