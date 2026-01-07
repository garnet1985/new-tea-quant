#!/usr/bin/env python3
"""
Momentum Strategy Settings - 动量策略配置
"""

settings = {
    "name": "momentum",
    "version": "1.0",
    "description": "动量策略 - 基于价格趋势的买入信号",
    
    "core": {
        "entity_type": "stock",
        "start_date": "20240101",
        "end_date": "20241231"
    },
    
    "performance": {
        "max_workers": 8
    },
    
    "data_requirements": {
        "base_entity": "stock_kline_daily",
        "required_entities": []
    },
    
    "execution": {
        "stop_loss": -0.05,      # -5% 止损
        "take_profit": 0.10,     # +10% 止盈
        "max_holding_days": 20   # 最大持有 20 天
    },
    
    "params": {
        "momentum_threshold": 0.05,   # 动量阈值（5%）
        "lookback_days": 60           # 历史窗口（60 天）
    }
}
