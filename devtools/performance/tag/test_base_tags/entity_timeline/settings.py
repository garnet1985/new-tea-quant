"""
Entity Timeline 基准 Tag 场景（settings.py）

简化版市值档位分类，用于性能基线测试。
仅在档位变化日写入 tag，代表典型的轻量级时间序列打标场景。

频率：每周计算一次（周五），降低写入频率以减少 IO 开销。
"""
settings = {
    "is_enabled": True,

    "meta": {
        "key": "bench_timeline",
        "display_name": "Benchmark Timeline",
        "description": "性能测试基准：entity_based 模式的轻量级市值分档（周频）",
        "keywords": ["benchmark", "performance", "timeline", "weekly"],
    },

    "core": {
        "micro_cap_max_threshold": 10.0,
        "low_cap_max_threshold": 30.0,
        "mid_cap_max_threshold": 100.0,
        "frequency": "weekly",
        "weekday": 4,
    },

    "calculation": {
        "update_mode": "incremental",
        "recompute": True,
        "execution": {
            "mode": "entity_based",
            "start_date": "",
            "end_date": "",
        },
    },

    "data": {
        "base": {
            "data_key": "stock.kline.daily",
            "params": {"adjust": "qfq"},
        },
        "required": [
            {"data_key": "stock.indicators.daily", "params": {}},
        ],
        "min_required_records": 1,
    },

    "tag_definitions": [
        {
            "name": "bench_cap_tier",
            "display_name": "Bench Cap Tier",
            "description": (
                "性能测试用：micro/low/mid/high 四档（周频），"
                "仅在档位变化日且为指定星期几时写入"
            ),
        },
    ],
}
