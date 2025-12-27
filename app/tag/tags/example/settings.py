"""
Tag 配置示例（settings.py）

新设计：支持一个 Calculator 打多个 Tag

配置结构：
1. calculator: Calculator 级别配置（共享逻辑）
2. tags: Tag 级别配置（一个 Calculator 下多个 tag）
"""
from app.tag.enums import KlineTerm, UpdateMode, VersionChangeAction

Settings = {
    # ========================================================================
    # Calculator 级别配置（共享逻辑）
    # ========================================================================
    "calculator": {
        "meta": {
            "name": "MARKET_VALUE_BUCKET",  # 业务逻辑名字，不是 tag 名
            "description": "按市值阈值给股票打大小市值标签",
            "is_enabled": True,
        },
        
        # 基础周期（迭代粒度）
        "base_term": KlineTerm.DAILY.value,
        
        # 需要的 K 线周期（可选）
        "required_terms": [],  # 如果只用日线可以空
        
        # 数据依赖（除了 kline 之外的其他数据源）
        "required_data": [
            # "corporate_finance",  # 示例：如果需要财务数据
        ],
        
        # Calculator 级别的 core 参数（共享给所有 tag）
        "core": {
            "mkv_threshold": 1e10,  # 市值阈值（100 亿）
        },
        
        # Calculator 级别的 performance 配置（可以被 tag 覆盖）
        "performance": {
            "max_workers": 8,  # 可选，默认自动分配
            "update_mode": UpdateMode.INCREMENTAL.value,  # 可选，有默认值
            "on_version_change": VersionChangeAction.REFRESH_SCENARIO.value,  # 可选，有默认值
        },
    },
    
    # ========================================================================
    # Tag 级配置（一个 Calculator 下多个 tag）
    # ========================================================================
    "tags": [
        {
            "name": "large_market_value",
            "display_name": "大市值股票",
            "description": "市值大于阈值的股票",
            "version": "1.0",
            # 注意：is_enabled 只在 calculator.meta 级别
            # 业务场景启用时，所有 tags 都会被计算
            
            # 这个 tag 自己特殊的参数（如果有的话）
            # tag.core 会合并到 calculator.core（tag 覆盖 calculator）
            "core": {
                "label": "large",  # 举例，可有可无
            },
            
            # 如果有特殊的 update_mode / on_version_change 也可以在这里 override
            # 否则继承 calculator.performance
            # "performance": {
            #     "update_mode": UpdateMode.REFRESH.value,  # 覆盖 calculator 的配置
            # },
        },
        {
            "name": "small_market_value",
            "display_name": "小市值股票",
            "description": "市值小于等于阈值的股票",
            "version": "1.0",
            # 注意：is_enabled 只在 calculator.meta 级别
            
            "core": {
                "label": "small",
            },
        },
    ],
}
