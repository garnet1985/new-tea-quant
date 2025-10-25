from app.data_source.enums import KlineTerm, AdjustType
from app.conf.conf import data_default_start_date

settings = {
    # 策略启用状态
    "is_enabled": False,

    "core": {
        # 你当前的策略是否需要额外的核心参数，如果有，请在这里配置
    },
    
    # 数据要求配置
    "klines": {
        # 数据周期 - 例子中指代模拟需要加在日，周，月线数据，模拟器会根据这个配置自动加载数据
        "terms": [KlineTerm.DAILY.value],
        # 信号检测周期 - 例子中指代基于日线检测信号
        "signal_base_term": KlineTerm.DAILY.value,
        # 模拟执行周期 - 例子中指代模拟器基于日线来进行一日日的模拟（交易日）
        "simulate_base_term": KlineTerm.DAILY.value,
        # 最小要求的基础周期记录数
        "min_required_base_records": 1000,
        # 复权方式
        "adjust": AdjustType.QFQ.value,
        # 要在K线上增加的技术指标
        "indicators": {
            # 移动平均线 (Simple Moving Average)
            "moving_average": {
                "periods": [5, 10, 20, 60],  # 计算多个周期的移动平均线
            },
            
            # MACD 指标 (Moving Average Convergence Divergence)
            "macd": {
                # 使用默认参数: fast=12, slow=26, signal=9
                "fast": 12,
                "slow": 26,
                "signal": 9,
            },
            
            # RSI 指标 (Relative Strength Index)
            "rsi": {
                "period": 14,  # RSI计算周期，默认14
            },
            
            # 布林带指标 (Bollinger Bands)
            "bollinger": {
                "period": 20,  # 布林带计算周期，默认20
                "std_multiplier": 2.0,  # 标准差倍数，默认2.0
            },

            # 是否使用股票的分类标签 - 标签类型见 labeler/conf/label_mapping.py
            "stock_labels": False
        },
    },

    "macro": {
        "GDP": True,
        "LPR": True,
        "Shibor": True,
        # 价格指数 - 空意味着取所有; 可用参数为: CPI, PPI, PMI, MoneySupply 
        "price_indexes": ["CPI", "PPI", "PMI", "MoneySupply"],
        "start_date": "",
        "end_date": "",
    },

    "corporate_finance": {
        # 公司财务指标 - 空意味着取所有; 可用参数为: growth, profit, cashflow, solvency, operation, asset
        "categories": ["growth", "profit", "cashflow", "solvency", "operation", "asset"],
        "start_date": "",
        "end_date": "",
    },


    "index_indicators": {
        # 指数指标 - 空意味着取所有; 可用参数为: sh_index(上证), sz_index(深证), hs_300(沪深300), cyb_index(创业板), kc_50(科创50)
        "categories": ["sh_index", "sz_index", "hs_300", "cyb_index", "kc_50"],
        "start_date": "",
        "end_date": "",
    },

    "industry_capital_flow": {
        # 行业资本流动
        "start_date": "",
        "end_date": "",
    },

    # 模拟时间范围 - 日期格式YYYYMMDD
    "simulation": {

        # 模拟开始日期 - 空指代使用默认开始日期
        "start_date": "",

        # 模拟结束日期 - 空指代到最新的记录
        "end_date": "",

        # 测试股票数量
        "sampling_amount": 10,

         # 是否记录模拟结果，结果会自动存在{folder_name}的tmp文件夹下
        "record_summary" : True,
        
        # 是否分析模拟结果，结果会自动存在{folder_name}的analysis文件夹下
        "analysis" : True,

        'sampling': {
            # 采样策略类型
            "strategy": "uniform",  # uniform, stratified, random, continuous, pool, blacklist
            
            # 各策略的专用配置
            "uniform": {
                # 均匀采样无需额外配置
                "description": "均匀间隔采样 - 每间隔N个股票抽取一个，结果可重现"
            },
            
            "stratified": {
                # 分层采样配置
                "seed": 42,  # 随机种子 - None表示每次运行都使用不同的随机种子
                "description": "分层采样 - 按市场类型（沪深主板，中小板，创业板，科创板）采样，科学合理，依赖seed"
            },
            
            "random": {
                # 随机采样配置
                "seed": 42,  # 随机种子 - None表示每次运行都使用不同的随机种子
                "description": "随机采样 - 随机抽取test_amount个股票，依赖seed保证可重现"
            },
            
            "continuous": {
                # 连续采样配置
                "start_idx": 0,  # 起始索引
                "description": "连续采样 - 从start_idx开始取test_amount个股票"
            },

            "pool": {
                # 股票池采样配置
                "stock_pool": ["000001.SZ", "000002.SZ", "000003.SZ", "000004.SZ", "000005.SZ", "000006.SZ", "000007.SZ", "000008.SZ", "000009.SZ", "000010.SZ"],
                "description": "股票池采样 - 从stock_pool中抽取test_amount个股票"
            },

            "blacklist": {
                # 黑名单采样配置
                "blacklist": ["000001.SZ", "000002.SZ", "000003.SZ", "000004.SZ", "000005.SZ", "000006.SZ", "000007.SZ", "000008.SZ", "000009.SZ", "000010.SZ"],
                "description": "黑名单采样 - 从blacklist中抽取test_amount个股票"
            },
        },
    },


    # 投资目标设置
    "goal": {
        # 固定期限强制平仓（可选，仅用于到期平仓，不属于止盈/止损）。
        # 如不配置，框架不会进行“到期平仓”判断；可同时配置自然日与交易日。
        # 到期时默认对剩余仓位执行结算。
        "fixed_days": 30,
        # "fixed_trading_days": 20,

        # 止损目标设置
        "stop_loss": {
            # 自定义止损 - 可选, 如果定义，需要重写基类里的should_stop_loss方法
            # "is_customized": False,

            # 保本止损 - 可选
            "break_even": {
                "name": "break_even",
                "ratio": 0,
                # close invest 代表卖出剩余所有仓位
                "close_invest": True  # 止损时：清仓
            },
            # 动态止损（追损）- 可选
            "dynamic": {
                "name": "dynamic",
                # ratio 代表在止损设置后累计出现过的最高点的下方10%为止损值
                "ratio": -0.1,
                "close_invest": True  # 动态止损时：清仓
            },
            # 分段止损 - 可选（至少一个阶段）
            "stages": [
                # 止损阶段
                {
                    # 名字随便取，只负责展示
                    "name": "loss20%",
                    # 当前价格低于买入价格的20%时触发止损
                    "ratio": -0.2,
                    # 止损行为是卖出所有仓位
                    "sell_ratio": 0.5,
                    # 新增（可选）：阶段触发时调整到期平仓规则
                    # 正为增加，负为减少；取消为 True 则不再生效
                    # "extend_fixed_days": 5,
                    # "cancel_fixed_days": false,
                    # "extend_fixed_trading_days": -2,
                    # "cancel_fixed_trading_days": false
                },
                # 止损阶段
                {
                    # 名字随便取，只负责展示
                    "name": "loss30%",
                    # 当前价格低于买入价格的30%时触发止损
                    "ratio": -0.3,
                    # 止损行为是卖出所有剩余仓位
                    "close_invest": True
                }
                # 止损阶段
                # {
                #     # 名字随便取，只负责展示
                #     "name": "fixed_days_expiry%",
                #     # 固定天数到期时触发止损
                #     "fixed_days": 30,
                #     # 止损行为是卖出所有剩余仓位
                #     "close_invest": True
                # }
            ]
        },
        # 止盈目标设置
        "take_profit": {
            # 自定义止盈 - 可选, 如果定义，需要重写基类里的should_take_profit方法
            # "is_customized": False,

            # 分段止盈 - 可选（至少一个阶段）
            "stages": [
                {
                    "name": "win10%",
                    # 当前价格高于买入价格的10%时触发止盈
                    "ratio": 0.1,
                    # 止盈时：卖出总仓位的20%
                    "sell_ratio": 0.2,  
                    # 止盈时：启动保本止损
                    "set_stop_loss": "break_even",
                    # 新增（可选）：阶段触发时调整到期平仓规则
                    # "extend_fixed_days": 3,
                    # "cancel_fixed_days": false,
                    # "extend_fixed_trading_days": 0,
                    # "cancel_fixed_trading_days": false
                },
                {
                    "name": "win20%",
                    "ratio": 0.2,
                    "sell_ratio": 0.2 
                },
                {
                    "name": "win30%",
                    "ratio": 0.3,
                    # 止盈时：启动动态止损
                    "set_stop_loss": "dynamic",
                    # 例如：达到 30% 后，取消自然日 fixed_days 到期
                    # "cancel_fixed_days": true
                }
            ]
        },
    },
}