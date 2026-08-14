#!/usr/bin/env python3
"""美股市场配置（US Stock Market Settings）。"""

settings = {
    "key": "us_stock",

    "meta": {
        "name": "美股市场",
        "description": "美国股票市场交易规则",
    },

    "settlement": {
        "t_plus": 0
    },

    "amplitude_limit": {
        "default_ratio": 0.0,
        "price_round_decimals": 2
    },

    "lot_size": {
        "default_min_lot": 1,
        "default_lot_step": 1
    }
}