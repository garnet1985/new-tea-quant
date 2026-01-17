from core.global_enums.enums import TermType, AdjustType
from core.infra.project_context import ConfigManager

settings = {
    # 策略启用状态
    "is_enabled": False,

    "core": {
        # 你当前的策略是否需要额外的核心参数，如果有，请在这里配置
    },
    
    # 数据要求配置
    "klines": {
        # 数据周期 - 例子中指代模拟需要加在日，周，月线数据，模拟器会根据这个配置自动加载数据
        "terms": [TermType.DAILY.value],
        # 信号检测周期 - 例子中指代基于日线检测信号
        "signal_base_term": TermType.DAILY.value,
        # 模拟执行周期 - 例子中指代模拟器基于日线来进行一日日的模拟（交易日）
        "simulate_base_term": TermType.DAILY.value,
        # 最小要求的基础周期记录数
        "min_required_base_records": 100,
        # 复权方式
        "adjust": AdjustType.QFQ.value,
        # 要在K线上增加的技术指标
    },

    "macro": {
        "LPR": True,
        "Shibor": True,
        "start_date": "",
        "end_date": "",
    },

    "corporate_finance": {
        # 公司财务指标 - 空意味着取所有; 可用参数为: growth, profit, cashflow, solvency, operation, asset
        "categories": ["solvency"],
        "start_date": "",
        "end_date": "",
    },


    # 模拟时间范围 - 日期格式YYYYMMDD
    "simulation": {

        # 模拟开始日期 - 空指代使用默认开始日期
        "start_date": "20180101",

        # 模拟结束日期 - 空指代到最新的记录
        "end_date": "",

        # 测试股票数量
        "sampling_amount": 1000,

         # 是否记录模拟结果，结果会自动存在{folder_name}的tmp文件夹下
        "record_summary" : True,
        
        # 是否分析模拟结果，结果会自动存在{folder_name}的analysis文件夹下
        "analysis" : True,

        'sampling': {
            # 采样策略类型
            "strategy": "continuous",  # uniform, stratified, random, continuous, pool, blacklist
            
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
        },
    },


    # 投资目标设置
    "goal": {
        # 固定期限强制平仓（可选，仅用于到期平仓，不属于止盈/止损）。
        # 如不配置，框架不会进行“到期平仓”判断；可同时配置自然日与交易日。
        # 到期时默认对剩余仓位执行结算。
        # "expiration": {
        #     "fixed_period": 30,
        #     "is_trading_period": True,
        # },

        # fixed days 是交易日还是自然日，默认是交易日
        # "is_trading_days": True,

        # 保本止损 - 可选
        # "protect_loss": {
        #     "ratio": 0,
        #     # close invest 代表卖出剩余所有仓位
        #     "close_invest": True  # 止损时：清仓
        # },
        # # 动态止损（追损）- 可选
        # "dynamic_loss": {
        #     # ratio 代表在止损设置后累计出现过的最高点的下方10%为止损值
        #     "ratio": -0.1,
        #     "close_invest": True  # 动态止损时：清仓
        # },

        # 止损目标设置
        "stop_loss": {
            # 自定义止损 - 可选, 如果定义，需要重写基类里的should_stop_loss方法
            # "is_customized": False,

            # 分段止损 - 可选（至少一个阶段）
            "stages": [
                # 止损阶段
                {
                    # 名字随便取，只负责展示
                    "name": "loss20%",
                    # 当前价格低于买入价格的20%时触发止损
                    "ratio": -0.2,
                    # 止损行为是卖出所有仓位
                    "close_invest": True,
                }
            ]
        },
        # 止盈目标设置
        "take_profit": {
            # 自定义止盈 - 可选, 如果定义，需要重写基类里的should_take_profit方法
            # "is_customized": False,

            # 分段止盈 - 可选（至少一个阶段）
            "stages": [
                {
                    "name": "win30%",
                    "ratio": 0.3,
                    "sell_ratio": 0.5,
                    # 止盈时：启动动态止损
                },
                {
                    "name": "win40%",
                    "ratio": 0.4,
                    "sell_ratio": 0.5,
                    # 止盈时：启动动态止损
                }
            ]
        },
    },
}