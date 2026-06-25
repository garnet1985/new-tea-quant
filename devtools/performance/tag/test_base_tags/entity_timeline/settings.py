"""
Entity Timeline 基准 Tag 场景（settings.py）

简化版市值档位分类，用于性能基线测试。
仅在档位变化日写入 tag，代表典型的轻量级时间序列打标场景。

频率：每周计算一次（周五），降低写入频率以减少 IO 开销。
"""
Settings = {
    "is_enabled": True,

    "meta": {
        "display_name": "Benchmark Timeline",
        "description": "性能测试基准：Entity Timeline 模式的轻量级市值分档（周频）",
        "keywords": ["benchmark", "performance", "timeline", "weekly"],
    },

    "core": {
        # 阈值单位：亿元；库内 total_market_value 为万元
        "micro_cap_max_threshold": 10.0,
        "low_cap_max_threshold": 30.0,
        "mid_cap_max_threshold": 100.0,
        # 计算频率：weekly（每周五）或 daily（每日）
        "frequency": "weekly",
        # 周几计算（0=周一, 4=周五）
        "weekday": 4,
    },

    "calculation": {
        "update_mode": "incremental",
        "recompute": True,
        "execution_mode": "entity_timeline",
        "start_date": "",
        "end_date": "",
    },

    "data": {
        "base_required_data": {
            "data_id": "stock.kline.daily",
            "params": {"adjust": "qfq"},
        },
        "extra_required_data_sources": [
            {"data_id": "stock.indicators.daily", "params": {}},
        ],
        "min_required_records": 1,
    },

    "tags": [
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
