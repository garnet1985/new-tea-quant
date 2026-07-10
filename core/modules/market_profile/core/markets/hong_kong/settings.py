#!/usr/bin/env python3
"""港股市场配置（Hong Kong Market Settings）。"""

settings = {
    "key": "hong_kong",

    "meta": {
        "name": "港股市场",
        "description": "香港股票市场交易规则",
    },

    "settlement": {
        "t_plus": 0
    },

    "amplitude_limit": {
        "default_ratio": 0.0,
        "price_round_decimals": 3
    },

    "lot_size": {
        "default_min_lot": 100,
        "default_lot_step": 100
    }
}