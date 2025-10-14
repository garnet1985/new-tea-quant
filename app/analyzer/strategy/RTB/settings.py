settings = {
    # 策略启用状态
    "is_enabled": True,  # V8版本启用
    
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
        # 测试股票数量 - V8测试前20只
        "test_amount": 10,
        # 测试股票起始索引
        "start_idx": 0,
        # 模拟参考版本号
        "simulation_ref_version": "V8_Weekly",
        # 是否记录模拟结果，结果会自动存在{folder_name}的tmp文件夹下
        "record_summary" : True
    },

    # 日线数据要求
    "klines": {
        # 日线数据要求 - 例子中指代模拟需要加在日，周，月线数据，模拟器会根据这个配置自动加载数据
        "terms": ["daily", "weekly"],
        # 日线数据要求 - 例子中指代模拟器基于日线来进行一日日的模拟（交易日）
        "base_term": "weekly",
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

    # 投资目标设置 - V8优化版本
    "goal": {
        # 固定期限强制平仓（交易日优先尝试）
        # 暂时去掉时间限制，纯止损止盈
        # "fixed_trading_days": 120,

        # 是否自定义止损目标 - 如果有此属性且为true，则完全使用此属性来判断是否应该结算投资，以下属性均不生效
        'is_customized': False,
        
        # 止损目标设置 - 简化版：-20%止损
        "stop_loss": {
            "stages": [
                {
                    "name": "loss20%",
                    "ratio": -0.20,  # 简化：-20%止损
                    "close_invest": True  # 止损时：清仓
                }
            ]
        },
        # 止盈目标设置 - 简化版：20%止盈
        "take_profit": {
            "stages": [
                {
                    "name": "win20%",
                    "ratio": 0.20,  # 简化：20%止盈
                    "sell_ratio": 1.0,  # 全部平仓
                    "close_invest": True
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