from core.global_enums.enums import UpdateMode

Settings = {
    "is_enabled": False,
    "name": "macro_regime",
    "display_name": "宏观环境示例",
    "description": "general 类型 Tag 示例：根据宏观数据输出环境标签",
    "recompute": False,
    "tag_target_type": "general",
    "data": {
        "required": [
            {"data_id": "macro.gdp", "params": {}},
            {"data_id": "macro.cpi", "params": {}},
            {"data_id": "macro.pmi", "params": {}},
        ],
        "tag_time_axis_based_on": "macro.gdp",
    },
    "update_mode": UpdateMode.INCREMENTAL.value,
    "incremental_required_records_before_as_of_date": 0,
    "core": {},
    "performance": {
        "max_workers": "auto",
    },
    "tags": [
        {
            "name": "macro_regime",
            "display_name": "宏观环境",
            "description": "示例：仅演示 general 模式配置与执行链路",
        },
    ],
}
