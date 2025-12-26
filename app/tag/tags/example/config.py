"""
Tag 配置示例

根据用户反馈重新设计：
1. 默认基于 stock kline，required_data 只配置额外数据
2. base_term 指定 kline 的 term（用于迭代）
3. required_terms 指定需要的 kline 周期（可选，与 base_term 取并集）
4. calculator_class 不需要配置，系统自动加载当前目录下的 calculator.py
5. 移除 execution 配置（切片逻辑由用户在 Calculator 中自定义）
6. core 完全开放，只包含用户自定义的计算参数
7. 使用枚举减少用户输入错误（term, update_mode, on_version_change）

使用枚举（必需）：
- 导入枚举：from app.tag.enums import KlineTerm, UpdateMode, VersionChangeAction
- 使用枚举值：KlineTerm.DAILY.value, UpdateMode.INCREMENTAL.value

示例：
    from app.tag.enums import KlineTerm, UpdateMode, VersionChangeAction
    
    TAG_CONFIG = {
        "base_term": KlineTerm.DAILY.value,
        "required_terms": [KlineTerm.WEEKLY.value, KlineTerm.MONTHLY.value],
        "performance": {
            "update_mode": UpdateMode.INCREMENTAL.value,
            "on_version_change": VersionChangeAction.NEW_TAG.value,
        },
    }
"""

# 导入枚举（必需）
from app.tag.enums import KlineTerm, UpdateMode, VersionChangeAction

TAG_CONFIG = {
    # ========================================================================
    # 元信息（存储到数据库）
    # ========================================================================
    "meta": {
        # 版本号（用于文档和说明，不会存储到数据库）
        "version": "1.0",
        
        # 标签唯一代码（machine readable）
        # 规则：
        # - 必须唯一，不能与其他 tag 重复
        # - 建议使用大写字母和下划线（如 VOL_20D, MC_LARGE）
        # - 会存储到数据库 tag.name 字段
        # - 用于程序内部引用和查询

        "name": "EXAMPLE_TAG",
        
        # 标签显示名称（用户可见）
        # 规则：
        # - 可以是中文或英文
        # - 用于 UI 显示和文档说明
        # - 会存储到数据库 tag.display_name 字段
        "display_name": "示例 Tag",
        
        # Tag 描述（可选）
        # 说明：
        # - 用于文档和说明
        # - 不会存储到数据库
        # - 建议描述 tag 的用途、计算逻辑、使用场景等
        "description": "这是一个示例 Tag 配置，展示了所有可用字段",
    },
    
    # ========================================================================
    # 基础周期（迭代粒度）
    # ========================================================================
    # 说明：
    # - 指定 kline 的 term（用于迭代）
    # - 系统会按照 base_term 指定的周期迭代（每个交易日/每周/每月）
    # - 必须使用枚举值：KlineTerm.DAILY.value, KlineTerm.WEEKLY.value, KlineTerm.MONTHLY.value
    # 示例：
    # - base_term = KlineTerm.DAILY.value - 按每个交易日迭代
    # - base_term = KlineTerm.WEEKLY.value - 按每周迭代（自动处理休市周）
    # - base_term = KlineTerm.MONTHLY.value - 按月迭代
    # 注意：
    # - base_term 决定迭代粒度，系统按这个 term 的 kline 数据迭代
    "base_term": KlineTerm.DAILY.value,
    
    # ========================================================================
    # 需要的 K 线周期（可选）
    # ========================================================================
    # 说明：
    # - 指定需要哪些 term 的 kline 数据（用于计算）
    # - 如果为空列表 []，默认只使用 base_term 指定的 term
    # - 如果配置，系统会加载 required_terms 和 base_term 的并集
    # - 必须使用枚举值：KlineTerm.DAILY.value, KlineTerm.WEEKLY.value, KlineTerm.MONTHLY.value
    # 示例：
    # - required_terms = [] - 只使用 base_term 的 kline（如 daily）
    # - required_terms = [KlineTerm.WEEKLY.value, KlineTerm.MONTHLY.value] - 使用 daily（base_term）+ weekly + monthly
    # 注意：
    # - base_term 决定迭代粒度（系统按这个 term 迭代）
    # - required_terms 决定加载哪些 term 的 kline 数据（用于计算）
    # - 支持 [] 或 None（语义相同，都表示只使用 base_term）
    "required_terms": [],  # 或 [KlineTerm.WEEKLY.value, KlineTerm.MONTHLY.value]，None 也支持
    
    # ========================================================================
    # 数据依赖（Calculator 需要哪些历史数据，除了 kline）
    # ========================================================================
    # 说明：
    # - 默认基于 stock kline（由 base_term 和 required_terms 指定）
    # - required_data 只配置额外数据（除了 kline 之外的其他数据源）
    "required_data": [
        "corporate_finance",  # 财务数据（季度）
        # 其他数据源示例：
        # "stock_list",  # 股票列表
        # ... 其他 data_source 系统中定义的数据源
    ],
    
    # ========================================================================
    # 注意：execution 配置已移除
    # ========================================================================
    # 说明：
    # - 切片逻辑由用户在 Calculator 中自定义
    # - 每次迭代的 kline 数据包含时间信息，用户可以根据时间判断是否需要计算
    # - 这样设计的好处：
    #   1. 简化配置（减少配置层级）
    #   2. 更灵活（用户完全控制切片逻辑）
    #   3. 降低学习成本
    # 示例（在 Calculator 中）：
    # ```python
    # def calculate_tag(self, stock_id, as_of_date, historical_data):
    #     # 用户自定义切片逻辑
    #     if not self._is_month_start(as_of_date):
    #         return None  # 跳过，不计算
    #     
    #     # 计算 tag
    #     ...
    # ```
    
    # ========================================================================
    # 用户自定义计算参数（完全开放的结构）
    # ========================================================================
    "core": {
        # ✅ 说明：
        # - core 的结构完全由用户自定义
        # - Calculator 可以通过 self.tag_config['core'] 访问这些参数
        # - 系统不关心 core 的具体结构，只负责传递给 Calculator
        # - 参数可以是任意类型（int, float, str, list, dict 等）
        # - core 中不能有任何跨 tag 复用的属性（如 type, is_continuous 等）
        
        # 示例 1：市值分类
        "min_market_cap": 10000000000,  # 最小市值（100 亿）
        "max_market_cap": 50000000000,  # 最大市值（500 亿）
        
        # 示例 2：动量计算（注释掉，实际使用时取消注释）
        # "lookback_period": 20,  # 回看周期（20 天）
        # "threshold": 0.15,  # 阈值（15%）
        
        # 示例 3：市场状态（注释掉，实际使用时取消注释）
        # "trend_period": 60,  # 趋势判断周期
        # "volatility_threshold": 0.2,  # 波动率阈值
        
        # 使用方式（在 Calculator 中）：
        # ```python
        # class MyCalculator(BaseTagCalculator):
        #     def calculate_tag(self, entity_id, as_of_date, historical_data):
        #         # 获取参数
        #         min_cap = self.tag_config['core']['min_market_cap']
        #         max_cap = self.tag_config['core']['max_market_cap']
        #         
        #         # 使用参数进行计算
        #         ...
        # ```
    },
    
    # ========================================================================
    # 性能配置（执行相关）
    # ========================================================================
    "performance": {
        # 最大并行 worker 数
        # 说明：
        # - 控制同时计算多少个实体（如股票）
        # - 用于内存管理，避免内存爆炸
        # 规则：
        # - 建议值：5-10（根据内存情况调整）
        # - 如果内存充足，可以增大此值
        # - 如果内存紧张，可以减小此值
        # 注意：
        # - worker 可以是线程或进程（由系统实现决定）
        # - 每个 worker 处理一个实体
        # - 计算完成后立即存储并释放内存
        # - 继续下一批次
        "max_worker": 10,  # 默认 10
        
        # 更新模式（数据累积方式）
        # 可选值：
        # - UpdateMode.INCREMENTAL.value: 增量更新（默认）
        #     * 系统会记录每个 (stock_id, tag_id) 的最大 as_of_date
        #     * 增量计算时从最后计算时间点 + 1 天开始计算
        #     * 适用于：数据量大，不需要重新计算所有历史数据
        # - UpdateMode.REFRESH.value: 全量刷新
        #     * 每次计算都从股票的上市日期开始
        #     * 适用于：数据量小，或需要重新计算所有历史数据
        # 注意：
        # - 如果 tag 的算法改变，建议使用 UpdateMode.REFRESH.value 重新计算所有历史数据
        # - 或者创建新 tag（新的 name），保留旧数据
        "update_mode": UpdateMode.INCREMENTAL.value,

        # 版本变更时的行为（算法改变时的处理方式）
        # 说明：
        # - 当 tag 的算法改变（core 参数改变）时，系统如何处理
        # - 这是用户显式声明：算法改变后是覆盖原 tag 还是生成新 tag
        # 可选值：
        # - VersionChangeAction.NEW_TAG.value: 创建新 tag（推荐）
        #     * 系统会创建新的 tag（新的 name），保留旧数据
        #     * 适用于：需要保留历史数据，对比不同算法版本
        # - VersionChangeAction.FULL_REFRESH.value: 全量刷新
        #     * 系统会删除旧数据，重新计算所有历史数据
        #     * 适用于：算法只是微调，不需要保留旧版本
        # 注意：
        # - 系统会检测 core 参数的变化，触发版本变更处理
        # - 用户需要显式声明处理方式，避免意外覆盖数据
        "on_version_change": VersionChangeAction.NEW_TAG.value,
    },
}

# ============================================================================
# 配置验证（可选，但建议）
# ============================================================================

def validate_config(config: dict) -> bool:
    """
    验证配置是否有效
    
    可以添加配置验证逻辑，确保配置正确
    """
    from app.tag.enums import KlineTerm, UpdateMode, VersionChangeAction
    
    # 必需字段检查
    required_fields = ["meta", "required_data", "base_term", "core", "performance"]
    for field in required_fields:
        if field not in config:
            raise ValueError(f"配置缺少必需字段: {field}")
    
    # meta 必需字段
    meta_required = ["name", "display_name"]
    for field in meta_required:
        if field not in config["meta"]:
            raise ValueError(f"meta 缺少必需字段: {field}")
    
    # base_term 检查（使用枚举验证）
    if not isinstance(config["base_term"], str):
        raise ValueError("base_term 必须是字符串（枚举值）")
    valid_terms = [term.value for term in KlineTerm]
    if config["base_term"] not in valid_terms:
        raise ValueError(f"base_term 必须是 {valid_terms} 之一（使用 KlineTerm 枚举），当前值: {config['base_term']}")
    
    # required_terms 检查（可选，支持 [] 或 None）
    if "required_terms" in config:
        if config["required_terms"] is not None and not isinstance(config["required_terms"], list):
            raise ValueError("required_terms 必须是列表、空列表 [] 或 None")
        if config["required_terms"]:
            for term in config["required_terms"]:
                if term not in valid_terms:
                    raise ValueError(f"required_terms 中的值必须是 {valid_terms} 之一（使用 KlineTerm 枚举），当前值: {term}")
    
    # required_data 检查
    if not isinstance(config["required_data"], list):
        raise ValueError("required_data 必须是列表")
    # 注意：required_data 可以为空（如果只需要 kline 数据）
    
    # performance 检查
    if "update_mode" not in config["performance"]:
        raise ValueError("performance 缺少必需字段: update_mode")
    valid_update_modes = [mode.value for mode in UpdateMode]
    if config["performance"]["update_mode"] not in valid_update_modes:
        raise ValueError(f"performance.update_mode 必须是 {valid_update_modes} 之一（使用 UpdateMode 枚举），当前值: {config['performance']['update_mode']}")
    
    # on_version_change 检查（可选）
    if "on_version_change" in config["performance"]:
        valid_version_actions = [action.value for action in VersionChangeAction]
        if config["performance"]["on_version_change"] not in valid_version_actions:
            raise ValueError(f"performance.on_version_change 必须是 {valid_version_actions} 之一（使用 VersionChangeAction 枚举），当前值: {config['performance']['on_version_change']}")
    
    return True

# 如果直接运行此文件，验证配置
if __name__ == "__main__":
    validate_config(TAG_CONFIG)
    print("✅ 配置验证通过")
