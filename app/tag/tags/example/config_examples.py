"""
Tag 配置示例 - 常见场景

本文件展示了不同场景下的 Tag 配置示例，帮助用户理解如何配置自己的 Tag。
"""

# 导入枚举（必需）
from app.tag.enums import KlineTerm, UpdateMode, VersionChangeAction

# ============================================================================
# 场景 1：月动量（值缓存）
# ============================================================================

MONTHLY_MOMENTUM_CONFIG = {
    "meta": {
        "version": "1.0",
        "name": "MONTHLY_MOMENTUM",
        "display_name": "月动量",
        "description": "计算每个股票每月的动量值，用于横向切片和排序",
    },
    "base_term": KlineTerm.DAILY.value,  # 按日迭代
    "required_terms": [],  # 只需要 daily kline
    "required_data": [],  # 不需要额外数据
    "core": {
        # 用户自定义参数
        "lookback_period": 20,  # 回看 20 天计算动量
    },
    "performance": {
        "max_worker": 10,
        "update_mode": UpdateMode.INCREMENTAL.value,
        "on_version_change": VersionChangeAction.NEW_TAG.value,
    },
}

# 注意：切片逻辑在 Calculator 中实现
# 例如：只在每月第一天计算，其他日期返回 None

# ============================================================================
# 场景 2：市场状态（逐日判断）
# ============================================================================

MARKET_REGIME_CONFIG = {
    "meta": {
        "version": "1.0",
        "name": "MARKET_REGIME",
        "display_name": "市场状态",
        "description": "判断市场状态（牛市、震荡市、熊市），逐日判断",
    },
    "base_term": KlineTerm.DAILY.value,  # 按日迭代
    "required_terms": [],  # 只需要 daily kline
    "required_data": [],  # 不需要额外数据
    "core": {
        # 用户自定义参数
        "trend_period": 60,  # 趋势判断周期（60 天）
        "volatility_threshold": 0.2,  # 波动率阈值（20%）
    },
    "performance": {
        "max_worker": 10,
        "update_mode": UpdateMode.INCREMENTAL.value,
        "on_version_change": VersionChangeAction.NEW_TAG.value,
    },
}

# ============================================================================
# 场景 3：市值分类（需要财务数据）
# ============================================================================

MARKET_CAP_LARGE_CONFIG = {
    "meta": {
        "version": "1.0",
        "name": "MARKET_CAP_LARGE",
        "display_name": "大市值",
        "description": "判断股票是否为大市值（市值超过 100 亿）",
    },
    "base_term": KlineTerm.DAILY.value,  # 按日迭代，每日判断市值
    "required_terms": [],  # 只需要 daily kline
    "required_data": [
        "corporate_finance",  # 需要财务数据获取总股本
    ],
    "core": {
        # 用户自定义参数
        "min_market_cap": 10000000000,  # 最小市值（100 亿）
    },
    "performance": {
        "max_worker": 10,
        "update_mode": UpdateMode.INCREMENTAL.value,
        "on_version_change": VersionChangeAction.NEW_TAG.value,
    },
}

# ============================================================================
# 场景 4：需要多个 term 的 kline 数据
# ============================================================================

MULTI_TERM_CONFIG = {
    "meta": {
        "version": "1.0",
        "name": "MULTI_TERM_TAG",
        "display_name": "多周期 Tag",
        "description": "需要 daily、weekly、monthly 的 kline 数据",
    },
    "base_term": KlineTerm.DAILY.value,  # 按日迭代
    "required_terms": [
        KlineTerm.WEEKLY.value,  # 额外需要周线数据
        KlineTerm.MONTHLY.value,  # 额外需要月线数据
    ],
    "required_data": [],  # 不需要额外数据
    "core": {
        # 用户自定义参数
        "custom_param": "value",
    },
    "performance": {
        "max_worker": 10,
        "update_mode": UpdateMode.INCREMENTAL.value,
        "on_version_change": VersionChangeAction.NEW_TAG.value,
    },
}

# ============================================================================
# 场景 5：全量刷新模式
# ============================================================================

FULL_REFRESH_CONFIG = {
    "meta": {
        "version": "1.0",
        "name": "FULL_REFRESH_TAG",
        "display_name": "全量刷新 Tag",
        "description": "每次计算都重新计算所有历史数据",
    },
    "base_term": KlineTerm.DAILY.value,
    "required_terms": [],
    "required_data": [],
    "core": {
        "custom_param": "value",
    },
    "performance": {
        "max_worker": 10,
        "update_mode": UpdateMode.REFRESH.value,  # 全量刷新
        "on_version_change": VersionChangeAction.FULL_REFRESH.value,  # 版本变更时也全量刷新
    },
}
