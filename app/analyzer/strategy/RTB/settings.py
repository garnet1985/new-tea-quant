from app.data_source.enums import KlineTerm, AdjustType
from app.conf.conf import data_default_start_date

settings = {
    # 策略启用状态
    "is_enabled": True,  # V20.1优化策略启用（基于收益分布分析的止损止盈优化）

    "version": "V20.5",
    
    "core": {
        "convergence": {
            "days": 15,  # V20优化：基于2741次投资数据优化的收敛期
        },
        "stability": {
            "days": 8,  # V20优化：基于2741次投资数据优化的稳定期
        },
        "invest_range": {
            "lower_bound": 0.008,  # V20优化：基于2741次投资数据优化的买入区间
            "upper_bound": 0.008,
        },
    },

    # 模拟模式
    'mode': {
        # 是不是只模拟黑名单中的股票
        "blacklist_only": False,
        # 测试股票数量 - 设置为0会运行所有股票
        "test_amount": 500,
        # 模拟参考版本号
        "simulation_ref_version": "V20.4_No_Upper_Limit_BreakEven",
        # 是否记录模拟结果，结果会自动存在{folder_name}的tmp文件夹下
        "record_summary" : True
    },
    
    # 股票采样配置 - V19.0改进：独立的采样配置模块
    'sampling': {
        # 采样策略类型
        "strategy": "uniform",  # uniform, stratified, random, continuous
        
        # 各策略的专用配置
        "uniform": {
            # 均匀采样无需额外配置
            "description": "均匀间隔采样，分布均匀，结果可重现"
        },
        
        "stratified": {
            # 分层采样配置
            "seed": 42,  # 随机种子
            "description": "按市场分层采样，科学合理，依赖seed"
        },
        
        "random": {
            # 随机采样配置
            "seed": 42,  # 随机种子
            "description": "完全随机采样，依赖seed保证可重现"
        },
        
        "continuous": {
            # 连续采样配置
            "start_idx": 0,  # 起始索引
            "description": "连续采样，从start_idx开始取test_amount个"
        }
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

    # 投资目标设置
    "goal": {
        # 固定期限强制平仓（交易日优先尝试）
        # V16优化：设置200天时间止损（基于盈利样本171.8天平均时长）
        "fixed_trading_days": 200,

        # 是否自定义止损目标 - 如果有此属性且为true，则完全使用此属性来判断是否应该结算投资，以下属性均不生效
        'is_customized': False,

               # 止损目标设置 - V20优化版：-12%止损（基于2741次投资数据优化）
        "stop_loss": {

            "dynamic": {
                "name": "dynamic",
                "ratio": -0.1,  # V20.4优化：动态止损-12%，给股票更多上涨空间
                "close_invest": True  # 动态止损时：清仓
            },

            "stages": [
                {
                    "name": "loss18%",
                    "ratio": -0.18,  # V20优化：-12%止损（基于2741次投资数据优化）
                    "close_invest": True  # 止损时：清仓
                }
            ]
        },
        # 止盈目标设置 - V20.4优化版：移除上限，使用break even止损保护利润
        "take_profit": {
            "stages": [
                {
                    "name": "win20%",
                    "ratio": 0.2,  # 第一阶段：25%止盈
                    "sell_ratio": 0.4,  # 30%平仓
                },
                {
                    "name": "win30%",
                    "ratio": 0.3,  # 第二阶段：35%止盈
                    "sell_ratio": 0.4,  # 再平仓50%（累计80%）
                    "set_stop_loss": "dynamic"  # 第二次止盈后设置动态止损控制剩余仓位
                }
                # 注意：没有第三阶段止盈，最后20%仓位由动态止损控制，可以无限上涨
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