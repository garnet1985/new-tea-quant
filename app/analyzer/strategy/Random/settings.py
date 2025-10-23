from app.data_source.enums import KlineTerm, AdjustType
from app.conf.conf import data_default_start_date

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
        "sampling_amount": 200,

         # 是否记录模拟结果，结果会自动存在{folder_name}的tmp文件夹下
        "record_summary" : True,
        
        # 是否分析模拟结果，结果会自动存在{folder_name}的analysis文件夹下
        "analysis" : True,

        'sampling': {
            # 采样策略类型
            "strategy": "random",  # 使用随机采样
            
            # 各策略的专用配置
            "uniform": {
                # 均匀采样无需额外配置
                "description": "均匀间隔采样 - 每间隔N个股票抽取一个，结果可重现"
            },
        },
    },

    # 投资目标设置
    "goal": {
        "is_customized": False,

        "stop_loss": {
            "stages": [
                {
                    "name": "loss10%",
                    "ratio": -0.5,  # ML分析优化：-15%止损
                    "close_invest": True
                }
            ]
        },

        "take_profit": {
            "stages": [
                {
                    "name": "win15%",
                    "ratio": 0.5,
                    "sell_ratio": 1,
                }
            ]
        },
    },
}
