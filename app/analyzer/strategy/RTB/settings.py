from app.data_source.enums import KlineTerm, AdjustType
from app.conf.conf import data_default_start_date

settings = {
    # 策略启用状态
    "is_enabled": True,  # V18.2平衡策略启用
    
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
        "test_amount": 500,
        # 测试股票起始索引
        "start_idx": 0,
        # 模拟参考版本号
        "simulation_ref_version": "V18.2_Balanced",
        # 是否记录模拟结果，结果会自动存在{folder_name}的tmp文件夹下
        "record_summary" : True
    },

    # 数据要求配置
    "klines": {
        # 数据周期 - 例子中指代模拟需要加在日，周，月线数据，模拟器会根据这个配置自动加载数据
        "terms": [KlineTerm.DAILY.value, KlineTerm.WEEKLY.value],
        # 信号检测周期 - V16优化：基于周线检测信号，避免重复计算
        "signal_base_term": KlineTerm.WEEKLY.value,
        # 模拟执行周期 - 基于日线执行，精确的买卖时机
        "simulate_base_term": KlineTerm.DAILY.value,
        # 最小要求的基础周期记录数
        "min_required_base_records": 100,
        # 复权方式
        "adjust": AdjustType.QFQ.value,
        # 要在K线上增加的技术指标
        "indicators": {
            "moving_average": {
                "periods": [5, 10, 20, 60],
            },
            "rsi": {
                "period": 14,  # 14日RSI
            },
        },
        # 是否使用股票标签
        "stock_labels": True
    },

    # 模拟时间范围 - 日期格式YYYYMMDD
    "simulation": {
        # 模拟开始日期 - 空指代使用默认开始日期
        "start_date": "",
        # 模拟结束日期 - 空指代到最新的记录
        "end_date": ""
    },

           # 投资目标设置 - V12优化版本
    "goal": {
        # 固定期限强制平仓（交易日优先尝试）
        # V15优化：设置150天时间止损（基于ML分析）
        "fixed_trading_days": 200,

        # 是否自定义止损目标 - 如果有此属性且为true，则完全使用此属性来判断是否应该结算投资，以下属性均不生效
        'is_customized': False,

               # 止损目标设置 - V15优化版：-15%止损（基于ML分析）
        "stop_loss": {

            "dynamic": {
                "name": "dynamic",
                "ratio": -0.1,
                "close_invest": True  # 动态止损时：清仓
            },

            "stages": [
                {
                    "name": "loss15%",
                    "ratio": -0.15,  # V15优化：-15%止损（基于ML分析）
                    "close_invest": True  # 止损时：清仓
                }
            ]
        },
        # 止盈目标设置 - V12优化版：分阶段止盈
        "take_profit": {
            "stages": [
                {
                    "name": "win20%",
                    "ratio": 0.2,  # 第二阶段：25%止盈
                    "sell_ratio": 0.4,  # 50%平仓
                },
                {
                    "name": "win30%",
                    "ratio": 0.3,  # 第三阶段：35%止盈
                    "sell_ratio": 0.4,  # 全部平仓
                    "set_stop_loss": "dynamic"
                },

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