#!/usr/bin/env python3
"""外汇市场配置（Forex Market Settings）。"""

settings = {
    "key": "forex",

    "meta": {
        "name": "外汇市场",
        "description": "外汇市场交易规则（标准手、迷你手、微型手）",
    },

    "settlement": {
        "t_plus": 0
    },

    "amplitude_limit": {
        "default_ratio": 0.0,
        "price_round_decimals": 5
    },

    "lot_size": {
        "default_min_lot": 100000,
        "default_lot_step": 100000
    }
}