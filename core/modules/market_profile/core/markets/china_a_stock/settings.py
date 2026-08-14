#!/usr/bin/env python3
"""中国A股市场配置（China A Stock Market Settings）。"""

settings = {
    "key": "china_a_stock",

    "meta": {
        "name": "中国A股市场",
        "description": "中国A股市场的规则配置",
    },

    "settlement": {
        "t_plus": 1
    },

    "amplitude_limit": {
        "default_ratio": 0.1,
        "price_round_decimals": 2,
        "default_risk": {
            "st": {"ratio": 0.05},
            "star_st": {"ratio": 0.05}
        },
        "rules": [
            {
                "key": "ke_chuang_ban",
                "matching": {"id": {"start_with": ["688"]}},
                "ratio": 0.2
            },
            {
                "key": "chuang_ye_ban",
                "matching": {"id": {"start_with": ["300"]}},
                "ratio": 0.2
            },
            {
                "key": "bei_jiao_suo",
                "matching": {"id": {"start_with": ["43", "83", "87", "88", "92"]}},
                "ratio": 0.3
            }
        ]
    },

    "lot_size": {
        "default_min_lot": 100,
        "default_lot_step": 100,
        "rules": [
            {
                "key": "ke_chuang_ban",
                "matching": {"id": {"start_with": ["688"]}},
                "min_lot": 200,
                "lot_step": 1
            }
        ]
    },
}