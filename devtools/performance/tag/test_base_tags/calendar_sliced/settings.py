"""
Calendar Sliced 基准 Tag 场景（settings.py）

市值百分位排名：每日计算所有股票的市值百分位 (0-100)。
代表典型的横截面因子计算场景，需要当日全市场数据。
"""
Settings = {
    "is_enabled": True,

    "meta": {
        "display_name": "Benchmark Sliced Percentile",
        "description": "性能测试基准：Calendar Sliced 模式的横截面市值百分位",
        "keywords": ["benchmark", "performance", "sliced", "percentile"],
    },

    "core": {
        # 可选：是否写入变化检测（False = 每日都写，True = 仅变化时写）
        "write_on_change_only": False,
    },

    "calculation": {
        "update_mode": "refresh",
        "recompute": True,
        "execution_mode": "calendar_slice",
        "start_date": "",
        "end_date": "",
    },

    # 注意：performance 配置由 worker.json 统一管理，对用户隐身
    # 用户无法通过 settings.py 覆盖性能参数

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
            "name": "bench_cap_pct",
            "display_name": "Bench Cap Percentile",
            "description": (
                "性能测试用：市值百分位 (0-100)，"
                "每日基于全市场排序计算"
            ),
        },
    ],
}
