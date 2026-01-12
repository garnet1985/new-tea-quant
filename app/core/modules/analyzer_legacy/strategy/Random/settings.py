from app.core.global_enums.enums import KlineTerm, AdjustType
from app.core.conf.conf import data_default_start_date

settings = {
    # 策略启用状态
    "is_enabled": True,

    "core": {
        "investment_probability": 0.05,
        "lookback_days": 20,
        "profit_loss_ratio": 1.5,
    },
    
    # 数据要求配置
    "klines": {
        # 数据周期 - 需要日线数据来计算振幅
        "terms": [KlineTerm.DAILY.value, KlineTerm.WEEKLY.value],
        # 信号检测周期 - 基于日线检测信号
        "signal_base_term": KlineTerm.WEEKLY.value,
        # 模拟执行周期 - 基于日线进行模拟
        "simulate_base_term": KlineTerm.DAILY.value,
        # 最小要求的基础周期记录数
        "min_required_base_records": 30,
        # 复权方式
        "adjust": AdjustType.QFQ.value,
    },

    # 模拟时间范围 - 日期格式YYYYMMDD
    "simulation": {
        # 模拟开始日期 - 空指代使用默认开始日期
        "start_date": "",

        # 模拟结束日期 - 空指代到最新的记录
        "end_date": "",

        # 测试股票数量
        "sampling_amount": 2,

         # 是否记录模拟结果，结果会自动存在{folder_name}的tmp文件夹下
        "record_summary" : True,
        
        # 是否分析模拟结果，结果会自动存在{folder_name}的analysis文件夹下
        "analysis" : False,

        'sampling': {
            # 采样策略类型
            "strategy": "uniform",  # 使用随机采样
            
            # 各策略的专用配置
            "random": {
                "seed": None,  # 使用None表示每次运行都使用不同的随机种子
                "description": "随机采样 - 每次运行结果不同"
            },
        },
    },

    # 投资目标设置
    "goal": {
        "expiration": {
            "fixed_period": 10,
            "is_trading_period": True,
        },

        "protect_loss": {
            "ratio": 0.0,
            "close_invest": True
        },

        "dynamic_loss": {
            "ratio": -0.1,
            "close_invest": True
        },

        "stop_loss": {
            "stages": [
                {
                    "name": "loss15%",
                    "ratio": -0.15,
                    "close_invest": True
                }
            ]
        },

        "take_profit": {
            "stages": [
                {
                    "name": "win30%",
                    "ratio": 0.3,
                    "sell_ratio": 1
                }
            ]
        },
    },
}
