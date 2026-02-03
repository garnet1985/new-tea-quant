# Kline Handler 场景的框架支持分析

## 场景特点

Kline Handler 是一个特殊的数据源，具有以下特点：

1. **多个 API**：同一个数据源包含 3 个 API（daily_kline、weekly_kline、monthly_kline）
2. **多字段分组**：需要按 `(id, term)` 分组查询最新日期
3. **不同日期范围**：每个 API 需要不同的结束日期
   - daily: 最新交易日
   - weekly: 上周日
   - monthly: 上月最后一天
4. **周期特定更新规则**：不同周期有不同的更新判断逻辑
   - daily: 总是更新（如果 latest_date < end_date）
   - weekly: 只有当时间间隔 >= 1 周时才更新
   - monthly: 只有当时间间隔 >= 1 个月时才更新
5. **按股票逐个保存**：需要在 `on_after_execute_job_batch_for_single_stock` 中处理

## 框架支持情况

### ✅ 已支持的功能

1. **多字段分组查询**
   - 通过 `result_group_by.keys: ["id", "term"]` 配置
   - 框架自动按多字段分组查询最新日期
   - 返回复合键格式：`{"id::term": latest_date}`

2. **按实体创建 ApiJobBundle**
   - BaseHandler 自动为每个股票创建 ApiJobBundle
   - 每个 bundle 包含所有 API（daily/weekly/monthly）

3. **钩子机制**
   - `on_before_fetch`: 可以修改 ApiJob 的日期范围和参数
   - `on_after_execute_job_batch_for_single_stock`: 可以按股票逐个保存

4. **字段映射配置化**
   - 支持在 config 中配置 `field_mapping`
   - 框架自动应用字段映射

### ❌ 不支持的功能（需要自定义代码）

1. **不同 API 的日期范围**
   - **问题**：BaseHandler 的 `_build_job` 方法为所有 API 注入统一的日期范围
   - **代码位置**：`base_handler.py:244` - `add_date_range(apis, start_date, end_date)`
   - **当前解决方案**：在 `on_before_fetch` 中手动修改每个 ApiJob 的日期范围
   - **代码量**：约 50 行自定义代码

2. **周期特定的更新判断**
   - **问题**：框架的 `compute_entity_date_ranges` 使用统一的更新判断逻辑（基于 `renew_mode`）
   - **当前解决方案**：在 `_calculate_start_dates` 中实现周期特定的更新判断
   - **代码量**：约 30 行自定义代码（`_should_update` 方法）

3. **不同周期的结束日期计算**
   - **问题**：框架只计算一个统一的 `end_date`（基于 `latest_completed_trading_date`）
   - **当前解决方案**：在 `on_before_fetch` 中手动计算每个周期的结束日期
   - **代码量**：约 10 行自定义代码

## 当前实现的工作量

Kline Handler 需要约 **100+ 行自定义代码**来处理框架不支持的功能：

1. `on_before_fetch` (约 100 行)
   - 计算不同周期的结束日期
   - 查询每个股票在每个周期的最新日期
   - 修改每个 ApiJob 的日期范围和参数

2. `_calculate_start_dates` (约 30 行)
   - 利用框架计算的日期范围
   - 应用周期特定的更新判断

3. `_should_update` (约 15 行)
   - 周期特定的更新判断逻辑

4. `_query_stock_latest_dates` (约 25 行)
   - 从框架的 `last_update_map` 中提取多字段分组数据

## 框架改进建议

### 方案 1：支持 per-API 日期范围配置（推荐）

在 API 配置中添加 `date_range` 配置：

```python
"apis": {
    "daily_kline": {
        "provider_name": "tushare",
        "method": "get_daily_kline",
        "max_per_minute": 700,
        "date_range": {
            "end_date": "latest_trading_date",  # 或函数引用
            "start_date": "from_last_update",  # 或函数引用
        },
    },
    "weekly_kline": {
        "date_range": {
            "end_date": "previous_week_end",
            "start_date": "from_last_update",
        },
    },
}
```

**优点**：
- 配置化，减少自定义代码
- 支持更多场景（不只是 kline）

**缺点**：
- 需要扩展配置格式
- 需要实现日期计算函数注册机制

### 方案 2：支持周期特定的更新规则配置

在 `renew` 配置中添加 `update_rules`：

```python
"renew": {
    "type": "incremental",
    "update_rules": {
        "daily": {"min_interval_days": 0},
        "weekly": {"min_interval_days": 7},
        "monthly": {"min_interval_periods": 1, "period_type": "month"},
    },
}
```

**优点**：
- 配置化更新规则
- 减少自定义代码

**缺点**：
- 需要扩展配置格式
- 需要实现更新规则引擎

### 方案 3：支持多字段分组的日期范围计算（已部分实现）

当前已支持多字段分组查询，但日期范围计算仍使用单字段逻辑。

**改进**：
- 在 `compute_entity_date_ranges` 中，如果检测到多字段分组，为每个复合键计算日期范围
- 在 `_build_jobs` 中，支持从复合键的日期范围中提取对应 API 的日期范围

**优点**：
- 利用现有框架能力
- 减少自定义代码

**缺点**：
- 仍然需要处理不同 API 的结束日期问题

## 总结

### 框架支持度评分：6/10

**支持良好的方面**：
- ✅ 多字段分组查询
- ✅ 按实体创建任务
- ✅ 钩子机制灵活

**支持不足的方面**：
- ❌ 不同 API 的日期范围（需要 50+ 行自定义代码）
- ❌ 周期特定的更新规则（需要 30+ 行自定义代码）
- ❌ 不同周期的结束日期计算（需要 10+ 行自定义代码）

### 建议

1. **短期**：保持当前实现，通过钩子机制处理特殊需求
2. **中期**：实现方案 1（per-API 日期范围配置），可以显著减少自定义代码
3. **长期**：考虑方案 2（周期特定更新规则），进一步简化复杂场景

### 其他类似场景

如果未来有其他数据源需要：
- 多个 API 需要不同的日期范围
- 周期特定的更新规则

建议优先实现方案 1，这样可以覆盖更多场景。
