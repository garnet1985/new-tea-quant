from core.global_enums.enums import EntityType
from core.global_enums.enums import UpdateMode

Settings = {
    # ========================================================================
    # Scenario 配置（顶层配置）
    # ========================================================================
    "is_enabled": False,

    # 场景名（CLI: python start-cli.py -t --scenario activity-ratio20）
    "name": "activity-ratio20",

    # 增量更新：只在状态变化时写入 tag_value（避免每天重复写入，tag 多也不乱）
    #
    # How it works（核心逻辑）：
    # - 每个交易日计算一次 ratio20：
    #       ratio20 = amount_t / mean(amount_{t-19..t})
    # - 产生 2 个布尔标签：
    #       activity_high: ratio20 >= high_threshold
    #       activity_low : ratio20 <= low_threshold
    # - 仅当某只股票某个标签的布尔值与“上一次已写入的值”不同时，才写入 sys_tag_value 一条记录
    #   （本质是变化事件日志，而非每日快照）
    #
    # Demo 引导（策略变种建议）：
    # - 在活跃度高的股票里找 RSI 低（更偏“热股回调”）：
    #       activity_high && rsi14 <= 30
    # - 在活跃度低的股票里只买更极端的 RSI（更偏“冷门超卖”）：
    #       activity_low && rsi14 <= 20
    "recompute": False,
    "tag_target_type": "entity_based",

    "target_entity": {
        "type": EntityType.STOCK_KLINE_DAILY.value,
    },

    "display_name": "活跃度（成交额/20日均值）",
    "description": (
        "用 amount / 最近20个交易日平均 amount 作为活跃度。"
        "每天计算一次，但只记录 activity_high/activity_low 的状态变化（delta log）。"
    ),

    # 可选：留空使用系统默认起止日期（增量模式会从最后一次写入的 as_of_date 继续）
    "start_date": "",
    "end_date": "",

    # DataContract 声明（与 strategy 模块同款）
    "data": {
        "required": [
            {
                "data_id": "stock.kline",
                "params": {
                    "term": "daily",
                    "adjust": "qfq",
                },
            },
        ],
        # entity_based 模式可省略，默认走 target_entity 对应主轴
        # "tag_time_axis_based_on": "stock.kline",
    },

    "update_mode": UpdateMode.INCREMENTAL.value,

    # 计算 ratio20 至少需要 20 个交易日；留一点缓冲
    "incremental_required_records_before_as_of_date": 25,

    "core": {
        "window": 20,
        "high_threshold": 1.2,
        "low_threshold": 0.7,
    },

    "performance": {
        "max_workers": "auto",
    },

    # ========================================================================
    # Tag 级别配置（对应 sys_tag_definition，一个 Scenario 下多个 tags）
    # ========================================================================
    "tags": [
        {
            "name": "activity_high",
            "display_name": "活跃度高",
            "description": "amount / avg(amount, 20d) >= high_threshold",
        },
        {
            "name": "activity_low",
            "display_name": "活跃度低",
            "description": "amount / avg(amount, 20d) <= low_threshold",
        },
    ],
}

