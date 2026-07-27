"""
Calendar Sliced 基准 Tag 场景（settings.py）

市值百分位排名：每日计算所有股票的市值百分位 (0-100)。
代表典型的横截面因子计算场景，需要当日全市场数据。
"""
settings = {
    "is_enabled": True,

    "meta": {
        "key": "bench_sliced",
        "display_name": "Benchmark Sliced Percentile",
        "description": "性能测试基准：slice_based 模式的横截面市值百分位",
        "keywords": ["benchmark", "performance", "sliced", "percentile"],
    },

    "core": {
        "write_on_change_only": False,
    },

    "calculation": {
        "update_mode": "refresh",
        "recompute": True,
        "execution": {
            "mode": "slice_based",
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
            "name": "bench_cap_pct",
            "display_name": "Bench Cap Percentile",
            "description": (
                "性能测试用：市值百分位 (0-100)，"
                "每日基于全市场排序计算"
            ),
        },
    ],
}
