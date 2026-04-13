"""
Tag 配置示例（settings.py）

拷贝这个文件到你的scenario目录下，然后修改文件名为settings.py，并修改内容。

新设计：基于三层表结构（tag_scenario, tag_definition, tag_value）

配置结构：
1. scenario: Scenario 级别配置（对应 tag_scenario 表）
2. tags: Tag 级别配置（对应 tag_definition 表，一个 Scenario 下多个 tags）
3. calculator: Calculator 级别配置（计算逻辑相关，不存储到数据库）

注意：
- version 在 settings.scenario 中指定（对应 tag_scenario.version）
- is_legacy 不在 settings 中，在代码层面管理
- display_name 如果未指定，代码层面会默认使用 name
"""
from core.global_enums.enums import EntityType, IndicatorType
from core.modules.tag.core.enums import UpdateMode, VersionChangeAction

Settings = {
    # ========================================================================
    # Scenario 配置（顶层配置）
    # 每个Scenario对应一个calculator。
    # ========================================================================

    "is_enabled": True,

    # 必须参数
    # 业务场景机器识别代码。请使用字母数字，并使用下划线连接，不能用特殊字符, 比如空格等
    "name": "example",

    # 必须参数
    # 是不是重新生成所有tags
    # - 当为false时，会使用update mode来决定是否重新生成tags
    # - 当为true时，会重新生成所有tags
    "recompute": False,

    # 必须参数
    "target_entity": {
        # 目标实体类型。可选值：具体请参考app.enums.EntityType枚举。
        "type": EntityType.STOCK_KLINE_DAILY.value,

        # 可选参数
        # 目标实体的指标。可选值：具体请参考app.enums.IndicatorType枚举。
        "indicators": [
            {
                "name": IndicatorType.MACD.value,
                "params": {
                    "fast": 12,
                    "slow": 26,
                    "signal": 9,
                },
            },
            {
                "name": IndicatorType.RSI.value,
                "params": {
                    "period": 14,
                },
            },
        ],
    },

    # 可选参数
    # 业务场景UI显示名称
    "display_name": "示例场景",

    # 可选参数
    # 业务场景描述
    "description": "一个展示所有可用settings的示例",

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
    # - required_data / base_data_source 使用了不同的时间字段（可以用 per_source 覆写）
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
    "required_entities": [
        {
            "type": EntityType.GDP.value,
        },
        {
            "type": EntityType.STOCK_KLINE_WEEKLY.value,
            "indicators": [
                {
                    "name": IndicatorType.MACD.value,
                    "params": {
                        "fast": 12,
                        "slow": 26,
                        "signal": 9,
                    },
                },
            ],
        },
    ],

    # 可选参数，默认为 INCREMENTAL
    # 更新模式。可选值：
    # - INCREMENTAL: 增量更新：继续你上次产生的最新的一个tag的时间点后继续计算。
    # - REFRESH: 全量刷新：重新计算该Scenario下所有tags的值。
    "update_mode": UpdateMode.INCREMENTAL.value,

    # 可选参数，默认为 0
    # 在增量模式下，确保加载足够的历史数据（记录数）。
    # 用于计算tag时，确保往前N条记录的数据也在缓存中，避免数据不足导致计算失败。
    # 例如：动量计算需要60根K线，设置为60，框架会确保从as_of_date往前60条记录的数据也在缓存中。
    # 框架内部会自动转换为chunk数量（ceil(records / data_chunk_size)）。
    # 注意：只在INCREMENTAL模式下生效，REFRESH模式下会加载所有历史数据，不需要此配置。
    "incremental_required_records_before_as_of_date": 0,

    # 可选参数，默认为空字典
    # 可以自定义你自己的核心参数/阈值等在core里边。
    "core": {},

    # 可选参数，默认为空字典
    # 可以自定义你自己的性能配置/并发数等在performance里边。
    "performance": {
        # 可选参数，默认"auto"，会根据job数量自动分配worker
        "max_workers": "auto",

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
            "name": "example_tag_1",  

            # 可选参数，默认同name（代码层面处理）
            # 标签UI显示名称（对应 tag_definition.display_name）
            "display_name": "example tag 1",   

            # 可选参数，默认为空字符串
            # 标签描述（对应 tag_definition.description）
            "description": "标签1",
        },
        {
            "name": "example_tag_2",

            "display_name": "example tag 2",

            "description": "举例：当计算结果不是标签1的情况下就使用的标签2",
        },
    ],
}
