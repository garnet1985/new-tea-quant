#!/usr/bin/env python3
"""数字货币市场配置（Crypto Market Settings）。"""

settings = {
    "key": "crypto",

    "meta": {
        "name": "数字货币市场",
        "description": "数字货币交易规则（24小时交易，极小单位）",
    },

    "settlement": {
        "t_plus": 0
    },

    "amplitude_limit": {
        "default_ratio": 0.0,
        "price_round_decimals": 8
    },

    "lot_size": {
        "default_min_lot": 1,
        "default_lot_step": 1
    }
}