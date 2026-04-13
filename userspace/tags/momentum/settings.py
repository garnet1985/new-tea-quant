"""
Momentum Tag 配置（settings.py）

动量因子计算（60天）
计算公式：MOM = (P_t-60d / P_t-5d) - 1
其中：
- P_t-60d: 过去60个交易日的收盘价
- P_t-5d: 过去5个交易日的收盘价

说明：
- base_term 为 DAILY（日线），用于迭代每个交易日
- 检测月份变化，当月份变化时计算上个月的动量
- 使用日线数据计算动量值
- tag的value包含年月和动量值，格式：YYYYMM:value
"""
from core.global_enums.enums import EntityType
from core.global_enums.enums import UpdateMode

Settings = {
    # ========================================================================
    # Scenario 配置（顶层配置）
    # 每个Scenario对应一个calculator。
    # ========================================================================

    "is_enabled": False,

    # 必须参数
    # 业务场景机器识别代码。请使用字母数字，并使用下划线连接，不能用特殊字符, 比如空格等
    "name": "momentum_mid_term",

    # 必须参数
    # 是不是重新生成所有tags
    # - 当为false时，会使用update mode来决定是否重新生成tags
    # - 当为true时，会重新生成所有tags
    "recompute": False,

    # 必须参数
    "target_entity": {
        # 目标实体类型。可选值：具体请参考app.enums.EntityType枚举。
        "type": EntityType.STOCK_KLINE_DAILY.value,
    },

    # 可选参数
    # 业务场景UI显示名称
    "display_name": "股票动量（60天）",

    # 可选参数
    # 业务场景描述
    "description": "动量因子为过去 60 天的累计收益。计算公式：MOM = (P_t-60d / P_t-5d) - 1，其中 P_t-60d 为过去 60 个交易日的收盘价，P_t-5d 为过去 5 个交易日的收盘价。",

    # 可选参数，默认为空字符串: 使用系统级别默认开始日期data_default_start_date
    # 计算开始日期。格式为YYYYMMDD（字符串，如 "20200101"）
    # 如果为空字符串，使用系统默认值
    "start_date": "",

    # 可选参数，默认为空字符串: 使用系统级别默认结束日期latest_completed_trading_date
    # 计算结束日期。格式为YYYYMMDD（字符串，如 "20251231"）
    # 如果为空字符串，使用系统默认值
    "end_date": "",

    # 可选参数：时间轴配置（time_axis）
    #
    # 默认情况下，Tag 系统会把“时间”理解为字段名 `date`（K 线也是 `date`）。
    # 但在以下场景，你需要显式配置 time_axis：
    # - 你的数据时间字段不叫 `date`（例如叫 `dt` / `trade_date` / `ts` 等）
    # - 同一张数据里有多个时间字段（例如 `created_at` 和 `report_date`），需要指定用哪个作为 tag 的时间轴
    # - required_entities / required_data 使用了不同的时间字段（可以用 per_source 覆写）
    #
    # 说明：
    # - 对季度数据（例如 corporate_finance），系统默认使用 `quarter`；如需改也可用 per_source 覆写。
    # - 大部分基于 K 线的场景保持默认即可，无需改动。
    "time_axis": {
        # 全局默认时间字段名（默认 "date"）
        "field": "date",
        # 针对某个数据源单独指定时间字段名：
        # key 可以是 required_entities / required_data 中的名称（例如 "gdp"），
        # 也可以是 "corporate_finance" / "klines" 等内部约定的 key。
        "per_source": {
            # 示例：如果某个宏观数据源的时间字段叫 dt，可以这样配置：
            # "gdp": {"field": "dt"},
            #
            # 示例：如果你希望 corporate_finance 用 report_date 而不是 quarter（仅示意）：
            # "corporate_finance": {"field": "report_date"},
            #
            # 示例：如果你的自定义 kline 时间字段不叫 date（极少数情况）：
            # "klines": {"field": "trade_date"},
        },
    },

    # 可选参数，默认为空列表
    "required_entities": [],

    # 可选参数，默认为 INCREMENTAL
    # 更新模式。可选值：
    # - INCREMENTAL: 增量更新：继续你上次产生的最新的一个tag的时间点后继续计算。
    # - REFRESH: 全量刷新：重新计算该Scenario下所有tags的值。
    "update_mode": UpdateMode.INCREMENTAL.value,

    # 可选参数，默认为 0
    # 在增量模式下，确保加载足够的历史数据（记录数）。
    # 在INCREMENTAL模式下，默认加载最近更新时的date作为as of date，然后取前后2个chunk进行初始化
    # 如果chunk size无法满足下列配置的需求，会停止执行并且警告用户需要增加chunk size或者设置use chunk为false
    "incremental_required_records_before_as_of_date": 60,

    # 可选参数，默认为空字典
    # 可以自定义你自己的核心参数/阈值等在core里边。
    "core": {
        "tag_interval": "monthly",  # 按月计算tag
    },

    # 可选参数，默认为空字典
    # 可以自定义你自己的性能配置/并发数等在performance里边。
    "performance": {
        # 可选参数，默认"auto"，会根据job数量自动分配worker
        "max_workers": "auto",


        "use_chunk": True,

        # 可选参数，默认为 500
        # 运行时数据切片大小（记录数）。切片越大，运行时内存占用越小但IO次数越多
        "data_chunk_size": 500,
    },

    
    # ========================================================================
    # Tag 级别配置（对应 tag_definition 表，一个 Scenario 下多个 tags）
    # ========================================================================
    "tags": [
        {
            # 必须参数
            # 标签的机器识别代码。请使用字母数字，并使用下划线连接，不能用特殊字符, 比如空格等（对应 tag_definition.name）
            "name": "momentum_60_days",

            # 可选参数，默认同name（代码层面处理）
            # 标签UI显示名称（对应 tag_definition.display_name）
            "display_name": "动量（60天）",

            # 可选参数，默认为空字符串
            # 标签描述（对应 tag_definition.description）
            "description": "根据最远60个交易日计算出的动量因子",
        }
    ],
}
