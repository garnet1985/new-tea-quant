"""
Tag 配置示例（settings.py）

拷贝该文件到你的 scenario 目录，并改名为 settings.py 后按需调整。
"""
from core.global_enums.enums import EntityType, UpdateMode

Settings = {
    # ========================================================================
    # Scenario 配置（顶层配置）
    # 每个Scenario对应一个calculator。
    # ========================================================================

    # 必须参数
    # 业务场景机器识别代码。请使用字母数字，并使用下划线连接，不能用特殊字符, 比如空格等
    "name": "example",

    "is_enabled": True,

    # 可选参数
    # 业务场景UI显示名称
    "display_name": "示例场景",

    # 可选参数
    # 业务场景描述
    "description": "一个展示所有可用settings的示例",

    # 为空时使用系统默认起始日期
    "start_date": "",

    # 为空时使用系统默认结束日期
    "end_date": "",

    # 必须参数
    # 是不是重新生成所有tags
    # - 当为false时，会使用update mode来决定是否重新生成tags
    # - 当为true时，会重新生成所有tags
    "recompute": False,
    "tag_target_type": "entity_based",  # entity_based | general

    # entity_based 模式建议提供；general 模式可省略
    "target_entity": {
        "type": EntityType.STOCK_KLINE_DAILY.value,
    },

    # DataContract 声明（与 strategy 模块同款）
    "data": {
        # 所有计算所需数据（统一列表）
        "required": [
            {"data_id": "stock.kline", "params": {"term": "daily", "adjust": "qfq"}},
            {"data_id": "macro.gdp", "params": {}},
            # {"data_id": "stock.finance.quarterly", "params": {}},
            # {"data_id": "tag", "params": {"scenario_name": "another_scenario", "entity_type": EntityType.STOCK_KLINE_DAILY.value}},
        ],
        # tag 的时间轴基于哪个 data_id：
        # - entity_based：可省略（默认 target_entity 对应主轴）
        # - general：必填
        # "tag_time_axis_based_on": "stock.kline",
    },

    # 更新模式：incremental / refresh
    "update_mode": UpdateMode.INCREMENTAL.value,

    # 增量模式下需要的历史窗口记录数
    "incremental_required_records_before_as_of_date": 0,

    # 可选参数，默认为空字典
    # 可以自定义你自己的核心参数/阈值等在core里边。
    "core": {},

    # 可选参数，默认为空字典
    # 可以自定义你自己的性能配置/并发数等在performance里边。
    "performance": {
        "max_workers": "auto",
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
