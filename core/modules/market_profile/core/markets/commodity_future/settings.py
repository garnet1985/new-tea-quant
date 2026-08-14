#!/usr/bin/env python3
"""商品期货市场配置（Commodity Future Market Settings）。"""

settings = {
    "key": "commodity_future",

    "meta": {
        "name": "商品期货市场",
        "description": "商品期货交易规则（能源化工、金属、农产品等）",
    },

    "settlement": {
        "t_plus": 0
    },

    "amplitude_limit": {
        "default_ratio": 0.08,
        "price_round_decimals": 2,
        "rules": [
            {
                "key": "energy",
                "matching": {"id": {"start_with": ["SC", "FU", "BU"]}},
                "ratio": 0.08
            },
            {
                "key": "metal",
                "matching": {"id": {"start_with": ["AU", "AG", "CU", "AL", "ZN", "PB", "NI", "SN"]}},
                "ratio": 0.06
            },
            {
                "key": "agriculture",
                "matching": {"id": {"start_with": ["A", "M", "Y", "P", "C", "CS", "JD", "L", "V", "PP", "EG", "MA", "TA", "SR", "CF", "OI", "RM"]}},
                "ratio": 0.04
            },
            {
                "key": "soft",
                "matching": {"id": {"start_with": ["SP", "AP", "CJ"]}},
                "ratio": 0.05
            }
        ]
    },

    "lot_size": {
        "default_min_lot": 1,
        "default_lot_step": 1
    }
}