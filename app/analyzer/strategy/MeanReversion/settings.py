"""
MeanReversion 策略配置
均值回归策略 - 基于价格偏离均线的历史分位数进行交易
"""

from app.data_source.enums import KlineTerm, AdjustType
from app.conf.conf import data_default_start_date

settings = {
    # 策略启用状态
    "is_enabled": False,
    
    # 策略核心参数
    "core": {
        "ma_period": 20,           # 均线周期
        "std_period": 20,          # 标准差计算周期
        "quantile_period": 120,     # 分位数计算周期（降低到60天）
        "lower_quantile": 0.05,    # 下分位数（15%，更宽松）
        "upper_quantile": 0.95,    # 上分位数（85%，更宽松）
    },

    # 数据要求配置
    "klines": {
        "terms": [KlineTerm.WEEKLY.value],
        "signal_base_term": KlineTerm.WEEKLY.value,
        "simulate_base_term": KlineTerm.WEEKLY.value,
        "min_required_base_records": 60,  # 至少需要60天数据计算分位数
        "adjust": AdjustType.QFQ.value,
        "indicators": {
            "moving_average": {
                "periods": [20],  # 只需要20日均线
            },
        },
        "stock_labels": False
    },

    # 模拟配置
    "simulation": {
        "start_date": data_default_start_date,
        "end_date": "",
        "sampling_amount": 5,
        "record_summary": True,
        "analysis": True,
        "sampling": {
            "strategy": "uniform",
            "uniform": {
                "description": "均匀间隔采样 - 每间隔N个股票抽取一个，结果可重现"
            }
        }
    },

    # 投资目标设置（支持细粒度customized）
    "goal": {
        # 自定义止损逻辑
        "stop_loss": {
            "stages": [
                {
                    "name": "loss8%",
                    "ratio": -0.08,
                    "close_invest": True
                }
            ]
        },
        
        # 传统止盈逻辑
        "take_profit": {
            "is_customized": True,
        },
    },
}
