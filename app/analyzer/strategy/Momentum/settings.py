"""
Momentum策略配置
"""
settings = {
    "is_enabled": True,
    "name": "Momentum",
    "key": "Momentum",
    "description": "动量投资策略 - 基于均线动量定期调仓",
    "version": "1.0.0",
    
    "core": {
        # 均线配置
        "short_ma": 20,      # 短期均线天数
        "long_ma": 60,       # 长期均线天数
        
        # 调仓周期
        "rebalance_period": "monthly",  # monthly, quarterly, yearly
        
        # 筛选配置
        "top_percentile": 0.10,  # 前10%动量最大的股票
        "top_n_max": 50,         # 最多选择N只股票（即使前10%超过N只）
        "top_n_min": 1,          # 最少选择1只股票
    },
    
    "klines": {
        "signal_base_term": "daily",     # 信号检测周期（日线）
        "simulate_base_term": "daily",   # 模拟执行周期（日线）
        "terms": ["daily"],
        "min_required_kline": 60,        # 最少需要60天数据
    },
    
    "sampling": {
        "strategy": "continuous",  # 使用continuous采样
    },
    
    "simulation": {
        "start_date": "",
        "end_date": "",
        "sampling_amount": 500,  # 使用10只股票进行测试
        "record_summary": True,
        "analysis": True,
        
        # 使用uniform采样 - 抽取部分股票
        "sampling": {
            "strategy": "uniform",
        },
    },
    
    "goal": {
        # 动量策略：周期结束时卖出
        "stop_loss": {
            "stages": []
        },
        "take_profit": {
            # 使用customized止盈，在周期结束时卖出
            "is_customized": True
        },
    },
}
