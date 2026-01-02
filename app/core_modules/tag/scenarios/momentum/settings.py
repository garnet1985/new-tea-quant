"""
Tag 配置示例（settings.py）

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
from app.core_modules.tag.core.enums import KlineTerm, UpdateMode, VersionChangeAction

Settings = {
    # ========================================================================
    # Scenario 级别配置（对应 tag_scenario 表）
    # 每个Scenario对应一个calculator。
    # ========================================================================

    "is_enabled": True,


    "scenario": {

        # 必须参数
        # 业务场景机器识别代码。请使用字母数字，并使用下划线连接，不能用特殊字符, 比如空格等（对应 tag_scenario.name）
        "name": "momentum_mid_term",  

        # 可选参数，默认同name
        # 业务场景UI显示名称（对应 tag_scenario.display_name）
        "display_name": "股票动量（60天）",      
        
        # 可选参数，默认为空字符串
        # 业务场景描述（对应 tag_scenario.description）
        "description": "动量因子为过去 60 天的累计收益",  
        # 动量计算公式：（过去 60 个交易日日的收益，排除最近 5 个交易日）
        # MOM = (P_t-60d / P_t-5d) - 1 
        # P_t-60d 为过去 60 个交易日的累计收益
        # P_t-5d 为过去 5 个交易日的累计收益


        # 必须参数
        # 版本号可以自己定义，字符串类型
        "version": "1.0",
        
        # 可选参数，默认为 REFRESH_SCENARIO
        # 定义如果检查到版本变更后该采取什么行为（Scenario 级别）。可选值：
        # - REFRESH_SCENARIO: 舍弃原来的tags，重新计算该Scenario下所有tags的值。
        # - NEW_SCENARIO: 保留原来版本的tags，创建一组新的tags。
        "on_version_change": VersionChangeAction.REFRESH_SCENARIO.value,
    },
    
    # ========================================================================
    # Calculator 级别配置（计算逻辑相关，不存储到数据库）
    # 每个calculator对应一个Scenario。
    # ========================================================================
    "calculator": {
        # 必须参数：
        # 基础周期（迭代粒度）可选值：
        # - DAILY: 日线
        # - WEEKLY: 周线
        # - MONTHLY: 月线
        "base_term": KlineTerm.DAILY.value,

        # 可选参数，默认为空字典
        # 可以自定义你自己的核心参数/阈值等在core里边。
        "core": {
            "tag_interval": "monthly",
        },
        
        # 可选参数，默认为空字典
        # 可以自定义你自己的性能配置/并发数等在performance里边。
        "performance": {
            # 可选参数，默认为 INCREMENTAL
            # 更新模式。可选值：
            # - INCREMENTAL: 增量更新：继续你上次产生的最新的一个tag的时间点后继续计算。
            # - REFRESH: 全量刷新：重新计算该Scenario下所有tags的值。
            "update_mode": UpdateMode.INCREMENTAL.value,  # 可选，有默认值
        },
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
