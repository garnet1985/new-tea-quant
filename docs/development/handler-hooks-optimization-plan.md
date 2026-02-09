# Handler 钩子函数优化建议

## 用户建议总结

### 1. `on_before_fetch` - 扩展 renew 行为 ✅
**用户观点**：可以扩展 renew 的一些行为，还有空间
**我的观点**：同意，需要先整理一下可以扩展的点

**可扩展的方向**：
- 日期范围计算的扩展（已有 `on_calculate_date_range`，但可以更灵活）
- 实体列表筛选逻辑（如增量更新判断）
- ApiJob 批量生成辅助方法

### 2. `on_after_fetch` - 业务逻辑 ✅
**用户观点**：都是业务逻辑，已经到了极限，暂时不用优化
**我的观点**：完全同意

### 3. `on_after_mapping` - 日期标准化内置 ⚠️
**用户观点**：大部分是业务改动，可能不用优化，但不确定日期标准化是否可以内置进 base handler
**我的观点**：可以内置，但需要配置化

**实现方案**：
- 在 `_normalize_data` 中，调用 `on_after_mapping` **之前**自动标准化日期
- 根据 `config.date_format` 自动判断：
  - 如果 `date_format` 为 `"day"`，自动标准化 `date` 字段为 `YYYYMMDD`
  - 如果 `date_format` 为 `"month"`，自动标准化 `date` 字段为 `YYYYMM`
  - 如果 `date_format` 为 `"quarter"`，自动标准化 `date` 字段为 `YYYYQN`
  - 如果 `date_format` 为 `"none"`，跳过日期标准化
- 如果 handler 需要标准化其他字段（如 `end_date`），可以在 `on_after_mapping` 中手动处理
- 如果 handler 不想使用默认的日期标准化，可以在 `on_after_mapping` 中重新处理

**优点**：
- 减少重复代码（3 个 handler 都在做日期标准化）
- 利用已有的 `date_format` 配置，无需额外配置
- 保持灵活性（handler 仍可在 `on_after_mapping` 中覆盖）

**缺点**：
- 只支持 `date` 字段，其他日期字段仍需手动处理
- 如果 handler 有特殊日期格式需求，仍需要手动处理

### 4. `on_after_normalize` - NaN 清洗内置 ✅✅
**用户观点**：清洗 NaN 可以内置进 `on_after_normalize` 前，默认清洗，除非声明不清洗
**我的观点**：强烈同意！这是最应该优化的点

**实现方案**：
- 在 `on_after_normalize` 的**默认实现**中自动调用 `clean_nan_in_normalized_data`
- 默认值策略：
  - 如果 `date_format` 为 `"day"` 或 `"month"`，默认值使用 `0.0`（数值数据）
  - 如果 `date_format` 为 `"quarter"` 或 `"none"`，默认值使用 `None`（可能包含非数值字段）
  - 或者统一使用 `None`，让 handler 自己决定
- 如果 handler 不想清洗，可以：
  - 复写 `on_after_normalize` 并直接返回 `normalized_data`
  - 或者在 config 中添加 `skip_nan_cleaning: true`（可选）

**优点**：
- 消除所有 handler 中的重复代码（6 个 handler 都在调用 `clean_nan_in_normalized_data`）
- 默认行为更合理（数据清洗应该是标准流程的一部分）
- 保持灵活性（handler 仍可覆盖）

**缺点**：
- 如果某个 handler 真的不需要清洗，需要额外配置（但这种情况应该很少）

### 5. 执行期保存钩子 - 业务逻辑 ✅
**用户观点**：这些是业务逻辑，不用优化
**我的观点**：完全同意

---

## 实现优先级

### 高优先级（立即实现）
1. **NaN 清洗内置** - 影响 6 个 handler，收益最大
2. **日期标准化内置** - 影响 3 个 handler，收益中等

### 中优先级（后续整理）
3. **`on_before_fetch` 扩展** - 需要先整理可以扩展的点，再决定如何实现

---

## 实现细节

### NaN 清洗内置实现

**修改 `BaseHandler.on_after_normalize`**：
```python
def on_after_normalize(self, context: Dict[str, Any], normalized_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    标准化后的钩子：默认行为是自动清洗 NaN 值，然后返回数据。
    
    子类可以覆盖此方法来自定义清洗逻辑，或跳过清洗（直接返回 normalized_data）。
    
    默认清洗策略：
    - 如果 config.date_format 为 "day" 或 "month"，默认值使用 0.0
    - 否则使用 None
    """
    config = context.get("config", {})
    date_format = (config.get("date_format") or "day").lower()
    
    # 根据 date_format 决定默认值
    if date_format in ("day", "month"):
        default = 0.0
    else:
        default = None
    
    # 自动清洗 NaN
    return self.clean_nan_in_normalized_data(normalized_data, default=default)
```

**影响**：
- `lpr`, `shibor`, `gdp`, `price_indexes`, `stock_index_indicator`, `stock_index_indicator_weight` 可以移除 `on_after_normalize` 中的 `clean_nan_in_normalized_data` 调用
- 如果某个 handler 需要不同的默认值，可以覆盖 `on_after_normalize`

### 日期标准化内置实现

**修改 `BaseHandler._normalize_data`**：
```python
# 在调用 on_after_mapping 之前
# 步骤 4.4：自动日期标准化（如果配置了 date_format）
config = context.get("config", {})
date_format = (config.get("date_format") or "day").lower()
if date_format != "none":
    from core.modules.data_source.service.normalization import normalization_helper as nh
    mapped_records = nh.normalize_date_field(
        mapped_records,
        field="date",
        target_format=date_format,  # 需要扩展 normalize_date_field 支持不同格式
    )

# 步骤 4.5：调用 on_after_mapping 钩子
mapped_records = self.on_after_mapping(context, mapped_records)
```

**影响**：
- `stock_index_indicator`, `stock_index_indicator_weight` 可以移除 `on_after_mapping` 中的日期标准化调用
- `latest_trading_date` 有特殊逻辑（提取最新日期），需要保留
- `price_indexes` 需要月份格式，可能需要特殊处理

**注意**：
- 需要扩展 `normalization_helper.normalize_date_field` 支持 `target_format` 参数
- 或者根据 `date_format` 自动判断目标格式

---

## 总结

| 优化项 | 优先级 | 收益 | 复杂度 | 用户同意度 |
|--------|--------|------|--------|-----------|
| NaN 清洗内置 | 高 | 高（6 个 handler） | 低 | ✅✅ 强烈同意 |
| 日期标准化内置 | 高 | 中（3 个 handler） | 中 | ⚠️ 不确定 |
| `on_before_fetch` 扩展 | 中 | 待评估 | 待评估 | ✅ 同意，需整理 |

**建议**：
1. 先实现 **NaN 清洗内置**（收益最大，复杂度最低）
2. 再实现 **日期标准化内置**（需要扩展 helper 方法）
3. 最后整理 **`on_before_fetch` 扩展**（需要先分析具体需求）
